import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func

from api.auth import Principal, get_current_principal, verify_tenant_access
from api.schemas import (
    CatalogItemBatchIngest,
    CatalogItemResponse,
    CatalogItemListResponse,
    CatalogRecommendationResponse,
    IngestResponse,
    ReprocessResponse,
)
from db.models import CatalogItem, CatalogRecommendation
from db.session import tenant_scoped_session, write_audit_log
from tasks.enrichment import enrich_catalog_item, reprocess_failed_items

router = APIRouter(prefix="/v1/catalogs", tags=["Catalogs"])


@router.post(
    "/{tenant_id}/items",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest raw catalog items for asynchronous enrichment",
)
def ingest_catalog_items(
    tenant_id: str,
    payload: CatalogItemBatchIngest,
    verified_tenant_id: str = Depends(verify_tenant_access),
    principal: Principal = Depends(get_current_principal),
):
    """
    Ingests a batch of catalog items under the tenant's context.
    Enqueues async Celery enrichment tasks and writes an audit log.
    """
    created_item_ids = []

    with tenant_scoped_session(verified_tenant_id) as db:
        for item_data in payload.items:
            item = CatalogItem(
                tenant_id=verified_tenant_id,
                sku=item_data.sku,
                raw_title=item_data.raw_title,
                raw_description=item_data.raw_description,
                status="pending",
            )
            db.add(item)
            db.flush()
            created_item_ids.append(item.id)

        # Mutating action audit entry
        write_audit_log(
            session=db,
            tenant_id=verified_tenant_id,
            actor=principal.actor,
            action="write",
            resource=f"catalog_items:batch_ingest:{len(created_item_ids)}_items",
        )

    # Enqueue async enrichment tasks after transaction commits successfully
    for item_id in created_item_ids:
        try:
            enrich_catalog_item.delay(str(verified_tenant_id), str(item_id))
        except Exception:
            # Fallback if Celery broker unavailable during test/dev
            pass

    return IngestResponse(
        message=f"Successfully ingested {len(created_item_ids)} catalog items.",
        ingested_count=len(created_item_ids),
        item_ids=created_item_ids,
    )


@router.get(
    "/{tenant_id}/items/{item_id}",
    response_model=CatalogItemResponse,
    summary="Retrieve single catalog item",
)
def get_catalog_item(
    tenant_id: str,
    item_id: str,
    verified_tenant_id: str = Depends(verify_tenant_access),
    principal: Principal = Depends(get_current_principal),
):
    """
    Reads an enriched catalog item.
    Crucial security note: If another tenant's item_id is requested,
    PostgreSQL RLS ensures 0 rows are returned, producing a 404 (Not Found).
    Never returns 403 to prevent leaking the existence of other tenants' records.
    """
    try:
        item_uuid = uuid.UUID(str(item_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    with tenant_scoped_session(verified_tenant_id) as db:
        item = db.execute(
            select(CatalogItem).where(CatalogItem.id == item_uuid)
        ).scalar_one_or_none()

        if not item:
            # Fail closed: Item not found within this tenant's RLS view
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        # Write read audit log
        write_audit_log(
            session=db,
            tenant_id=verified_tenant_id,
            actor=principal.actor,
            action="read",
            resource=f"catalog_items:{item.id}",
        )

        return item


@router.get(
    "/{tenant_id}/items",
    response_model=CatalogItemListResponse,
    summary="List paginated catalog items for tenant",
)
def list_catalog_items(
    tenant_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    verified_tenant_id: str = Depends(verify_tenant_access),
    principal: Principal = Depends(get_current_principal),
):
    with tenant_scoped_session(verified_tenant_id) as db:
        query = select(CatalogItem)
        if status_filter:
            query = query.where(CatalogItem.status == status_filter)

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
        items = db.execute(query.order_by(CatalogItem.created_at.desc()).offset(offset).limit(limit)).scalars().all()

        write_audit_log(
            session=db,
            tenant_id=verified_tenant_id,
            actor=principal.actor,
            action="read",
            resource=f"catalog_items:list:count_{len(items)}",
        )

        return CatalogItemListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )


@router.post(
    "/{tenant_id}/reprocess",
    response_model=ReprocessResponse,
    summary="Re-trigger enrichment for failed items",
)
def reprocess_failed_catalog_items(
    tenant_id: str,
    verified_tenant_id: str = Depends(verify_tenant_access),
    principal: Principal = Depends(get_current_principal),
):
    """Re-enqueues processing for catalog items with status 'failed'."""
    try:
        task = reprocess_failed_items.delay(str(verified_tenant_id))
        count = task.get(timeout=5) if hasattr(task, "get") else 0
    except Exception:
        # Fallback to direct re-enqueue
        count = 0
        with tenant_scoped_session(verified_tenant_id) as db:
            failed_items = db.execute(select(CatalogItem).where(CatalogItem.status == "failed")).scalars().all()
            for item in failed_items:
                item.status = "pending"
                enrich_catalog_item.delay(str(verified_tenant_id), str(item.id))
                count += 1
            write_audit_log(
                session=db,
                tenant_id=verified_tenant_id,
                actor=principal.actor,
                action="reprocess",
                resource=f"catalog_items:reprocess_batch:{count}",
            )

    return ReprocessResponse(
        message=f"Reprocessing initiated for {count} failed items.",
        enqueued_count=count,
    )


@router.get(
    "/{tenant_id}/recommendations/{item_id}",
    response_model=List[CatalogRecommendationResponse],
    summary="Get cross-sell / category recommendations for an item",
)
def get_recommendations(
    tenant_id: str,
    item_id: str,
    verified_tenant_id: str = Depends(verify_tenant_access),
    principal: Principal = Depends(get_current_principal),
):
    try:
        item_uuid = uuid.UUID(str(item_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    with tenant_scoped_session(verified_tenant_id) as db:
        # Verify source item exists within tenant scope
        source_item = db.execute(select(CatalogItem).where(CatalogItem.id == item_uuid)).scalar_one_or_none()
        if not source_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        recs = db.execute(
            select(CatalogRecommendation)
            .where(CatalogRecommendation.source_item_id == item_uuid)
            .order_by(CatalogRecommendation.score.desc())
        ).scalars().all()

        write_audit_log(
            session=db,
            tenant_id=verified_tenant_id,
            actor=principal.actor,
            action="read",
            resource=f"catalog_recommendations:{item_id}",
        )

        return recs

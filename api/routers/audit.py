from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func

from api.auth import Principal, get_current_principal, verify_tenant_access, require_auditor
from api.schemas import AccessAuditLogResponse, AuditLogListResponse
from db.models import AccessAuditLog
from db.session import tenant_scoped_session, auditor_scoped_session

router = APIRouter(tags=["Audit & Compliance"])


@router.get(
    "/v1/audit/{tenant_id}",
    response_model=AuditLogListResponse,
    summary="Get tenant's own audit trail",
)
def get_tenant_audit_trail(
    tenant_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action_filter: Optional[str] = Query(None, alias="action"),
    verified_tenant_id: str = Depends(verify_tenant_access),
    principal: Principal = Depends(get_current_principal),
):
    """
    Retrieves audit log entries for the authenticated tenant.
    Enforced by PostgreSQL RLS on the access_audit_log table.
    """
    with tenant_scoped_session(verified_tenant_id) as db:
        query = select(AccessAuditLog)
        if action_filter:
            query = query.where(AccessAuditLog.action == action_filter)

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
        logs = (
            db.execute(query.order_by(AccessAuditLog.occurred_at.desc()).offset(offset).limit(limit))
            .scalars()
            .all()
        )

        return AuditLogListResponse(
            logs=logs,
            total=total,
            limit=limit,
            offset=offset,
        )


@router.get(
    "/v1/admin/audit",
    response_model=AuditLogListResponse,
    summary="Cross-tenant compliance audit trail (auditor role only)",
)
def get_cross_tenant_audit_trail(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant_id_filter: Optional[str] = Query(None, alias="tenant_id"),
    action_filter: Optional[str] = Query(None, alias="action"),
    auditor: Principal = Depends(require_auditor),
):
    """
    Provides cross-tenant audit visibility for compliance and security reviewers.
    Uses PostgreSQL 'auditor_role' which possesses cross-tenant read privileges ONLY
    on access_audit_log (see §5.2 and §5.3).
    """
    with auditor_scoped_session() as db:
        query = select(AccessAuditLog)
        if tenant_id_filter:
            query = query.where(AccessAuditLog.tenant_id == tenant_id_filter)
        if action_filter:
            query = query.where(AccessAuditLog.action == action_filter)

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
        logs = (
            db.execute(query.order_by(AccessAuditLog.occurred_at.desc()).offset(offset).limit(limit))
            .scalars()
            .all()
        )

        return AuditLogListResponse(
            logs=logs,
            total=total,
            limit=limit,
            offset=offset,
        )

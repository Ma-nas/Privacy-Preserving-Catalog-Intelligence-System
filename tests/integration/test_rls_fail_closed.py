import pytest
import uuid
from sqlalchemy import text, select
from db.models import Tenant, CatalogItem, CatalogRecommendation, AccessAuditLog
from db.session import tenant_scoped_session, auditor_scoped_session
from db.engine import SessionLocal, AuditorSessionLocal


def test_rls_blocks_cross_tenant_access(db_session_factory, test_tenants):
    """
    §9.2 The RLS fail-closed test:
    Verify that tenant B querying for tenant A's catalog item sees zero rows,
    NOT tenant A's row, and NOT an error.
    """
    tenant_a, tenant_b = test_tenants

    # Insert an item belonging to tenant A using tenant A's scoped session
    with tenant_scoped_session(tenant_a.id) as db:
        item = CatalogItem(
            tenant_id=tenant_a.id,
            sku="SKU-TENANT-A-001",
            raw_title="Tenant A Wireless Noise Canceling Headphones",
            raw_description="High fidelity sound with active noise cancellation",
            status="pending",
        )
        db.add(item)
        db.flush()
        item_id = item.id

    # Verify tenant A can see their own item
    with tenant_scoped_session(tenant_a.id) as db:
        found_a = db.execute(select(CatalogItem).where(CatalogItem.id == item_id)).scalar_one_or_none()
        assert found_a is not None
        assert found_a.sku == "SKU-TENANT-A-001"

    # CRITICAL INVARIANT: Tenant B queries for Tenant A's item
    with tenant_scoped_session(tenant_b.id) as db:
        result = db.execute(select(CatalogItem).where(CatalogItem.id == item_id)).first()
        assert result is None, "Tenant B must see zero rows, not tenant A's item!"


def test_rls_fails_closed_when_context_unset(db_session_factory, test_tenants):
    """
    §9.2 Fail-closed guarantee:
    Simulate a bug where SET LOCAL app.tenant_id was never called.
    Because current_setting('app.tenant_id', true) returns NULL when unset,
    NULL = anything evaluates to NULL (falsy), so a session with unset context
    sees zero rows, never all rows.
    """
    tenant_a, _ = test_tenants

    # Seed an item for Tenant A
    with tenant_scoped_session(tenant_a.id) as db:
        item = CatalogItem(
            tenant_id=tenant_a.id,
            sku="SKU-TENANT-A-UNSET-TEST",
            raw_title="Sensitive Tenant A Hardware",
            status="pending",
        )
        db.add(item)
        db.flush()

    # Intentionally bypass tenant_scoped_session to test unset context behavior
    with SessionLocal() as raw_db:
        result = raw_db.execute(select(CatalogItem)).all()
        assert result == [], "Unset tenant context must fail-closed and return zero rows!"


def test_tenant_write_isolation_blocks_cross_tenant_insert(db_session_factory, test_tenants):
    """
    RLS WITH CHECK constraint verification:
    Tenant B cannot insert a row tagged with tenant A's ID.
    Postgres RLS will reject this with a policy check violation.
    """
    tenant_a, tenant_b = test_tenants

    with pytest.raises(Exception) as exc_info:
        with tenant_scoped_session(tenant_b.id) as db:
            adversarial_item = CatalogItem(
                tenant_id=tenant_a.id,  # Adversarial attempt: Tenant B inserting with Tenant A's ID
                sku="SKU-MALICIOUS-INJECT",
                raw_title="Spoofed Product",
            )
            db.add(adversarial_item)
            db.flush()

    # Verify RLS policy violation occurred
    assert "policy" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower() or "violates" in str(exc_info.value).lower()


def test_auditor_role_cross_tenant_read_access(db_session_factory, test_tenants):
    """
    Verify §5.3 DB roles:
    auditor_role has cross-tenant read-only access to access_audit_log,
    allowing compliance audits without bypassing tenant isolation on raw catalog data.
    """
    tenant_a, tenant_b = test_tenants

    # Tenant A logs an access
    with tenant_scoped_session(tenant_a.id) as db:
        audit_a = AccessAuditLog(
            tenant_id=tenant_a.id,
            actor="tenant_a_user",
            action="write",
            resource="catalog_items:batch-1",
        )
        db.add(audit_a)

    # Tenant B logs an access
    with tenant_scoped_session(tenant_b.id) as db:
        audit_b = AccessAuditLog(
            tenant_id=tenant_b.id,
            actor="tenant_b_user",
            action="write",
            resource="catalog_items:batch-2",
        )
        db.add(audit_b)

    # Auditor role queries the audit table
    with auditor_scoped_session() as auditor_db:
        all_logs = auditor_db.execute(select(AccessAuditLog)).scalars().all()
        tenant_ids_in_audit = {log.tenant_id for log in all_logs}
        assert tenant_a.id in tenant_ids_in_audit
        assert tenant_b.id in tenant_ids_in_audit

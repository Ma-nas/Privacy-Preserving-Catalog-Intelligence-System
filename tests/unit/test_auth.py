import uuid
import pytest
from fastapi import HTTPException
from api.auth import create_access_token, Principal, verify_tenant_access, require_auditor


def test_jwt_token_creation_and_payload():
    tenant_id = str(uuid.uuid4())
    token = create_access_token(
        tenant_id=tenant_id,
        actor="test_user@tenant.com",
        role="tenant_admin",
    )
    assert isinstance(token, str)
    assert len(token) > 20


def test_verify_tenant_access_matches():
    tenant_id = str(uuid.uuid4())
    principal = Principal(tenant_id=tenant_id, actor="valid_user", role="tenant_user")
    
    # Path matches principal tenant
    result = verify_tenant_access(tenant_id=tenant_id, principal=principal)
    assert result == tenant_id


def test_verify_tenant_access_blocks_cross_tenant_spoof():
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    principal = Principal(tenant_id=tenant_b, actor="malicious_user", role="tenant_user")

    # Principal from Tenant B attempting to access Tenant A's route
    with pytest.raises(HTTPException) as exc_info:
        verify_tenant_access(tenant_id=tenant_a, principal=principal)

    assert exc_info.value.status_code == 403
    assert "Cross-tenant access forbidden" in exc_info.value.detail


def test_require_auditor_permits_auditor():
    auditor_principal = Principal(actor="auditor_svc", role="auditor")
    res = require_auditor(auditor_principal)
    assert res.role == "auditor"


def test_require_auditor_rejects_regular_tenant():
    user_principal = Principal(tenant_id=str(uuid.uuid4()), actor="regular_user", role="tenant_user")
    with pytest.raises(HTTPException) as exc_info:
        require_auditor(user_principal)
    assert exc_info.value.status_code == 403

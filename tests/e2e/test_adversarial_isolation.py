import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app
from api.auth import create_access_token
from db.models import CatalogItem, CatalogRecommendation, AccessAuditLog

client = TestClient(app)


def test_adversarial_cross_tenant_item_access_returns_404():
    """
    Step 11 & §6.2 Adversarial Test:
    Tenant B attempts to access Tenant A's item_id under Tenant B's endpoint.
    Because PostgreSQL RLS filters out rows from other tenants,
    the lookup returns None and results in an HTTP 404 (Not Found).
    It MUST NOT return HTTP 403 (Forbidden) so it never confirms whether
    the ID exists for another tenant.
    """
    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())
    item_a_id = uuid.uuid4()

    # Generate legitimate JWT for Tenant B
    tenant_b_token = create_access_token(tenant_id=tenant_b_id, actor="attacker_user", role="tenant_user")
    headers = {"Authorization": f"Bearer {tenant_b_token}"}

    # Mock DB session to simulate PostgreSQL RLS returning None when querying another tenant's item
    with patch("api.routers.catalogs.tenant_scoped_session") as mock_session_ctx:
        mock_db = MagicMock()
        # RLS filter simulation: query returns None because tenant_id does not match
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_session_ctx.return_value.__enter__.return_value = mock_db

        # Adversarial request: Tenant B specifies their own route but Tenant A's item_id
        response = client.get(
            f"/v1/catalogs/{tenant_b_id}/items/{item_a_id}",
            headers=headers,
        )

        assert response.status_code == 404, (
            f"Expected 404 Not Found to prevent data existence leakage, but got {response.status_code}"
        )
        assert response.json()["detail"] == "Item not found"


def test_adversarial_route_spoofing_returns_403():
    """
    Tenant B attempts to access Tenant A's endpoint path directly (/v1/catalogs/{tenant_a}/...)
    using Tenant B's JWT token.
    API Layer cross-check (§6.2) immediately rejects the request with HTTP 403.
    """
    tenant_a_id = str(uuid.uuid4())
    tenant_b_id = str(uuid.uuid4())

    tenant_b_token = create_access_token(tenant_id=tenant_b_id, actor="attacker_user", role="tenant_user")
    headers = {"Authorization": f"Bearer {tenant_b_token}"}

    response = client.get(
        f"/v1/catalogs/{tenant_a_id}/items",
        headers=headers,
    )

    assert response.status_code == 403
    assert "Cross-tenant access forbidden" in response.json()["detail"]


def test_adversarial_recommendation_lookup_returns_404():
    """
    Tenant B attempts to read recommendations for Tenant A's item_id.
    Must return 404 Not Found.
    """
    tenant_b_id = str(uuid.uuid4())
    foreign_item_id = uuid.uuid4()

    tenant_b_token = create_access_token(tenant_id=tenant_b_id, actor="attacker_user", role="tenant_user")
    headers = {"Authorization": f"Bearer {tenant_b_token}"}

    with patch("api.routers.catalogs.tenant_scoped_session") as mock_session_ctx:
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_session_ctx.return_value.__enter__.return_value = mock_db

        response = client.get(
            f"/v1/catalogs/{tenant_b_id}/recommendations/{foreign_item_id}",
            headers=headers,
        )

        assert response.status_code == 404

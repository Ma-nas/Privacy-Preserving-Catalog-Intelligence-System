import uuid
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import text
from db.session import validate_tenant_id, write_audit_log, tenant_scoped_session
from db.models import AccessAuditLog


def test_validate_tenant_id_valid_uuid():
    valid_id = str(uuid.uuid4())
    result = validate_tenant_id(valid_id)
    assert result == valid_id


def test_validate_tenant_id_rejects_sql_injection():
    malicious_inputs = [
        "'; DROP TABLE tenants; --",
        "1 OR 1=1",
        "admin'--",
        "invalid-uuid-string",
        "",
    ]
    for bad_input in malicious_inputs:
        with pytest.raises(ValueError) as exc:
            validate_tenant_id(bad_input)
        assert "Must be a valid UUID" in str(exc.value)


def test_write_audit_log_creates_model():
    mock_session = MagicMock()
    tenant_id = str(uuid.uuid4())
    actor = "system_agent"
    action = "write"
    resource = "catalog_items:item-99"

    entry = write_audit_log(mock_session, tenant_id, actor, action, resource)

    assert entry.tenant_id == tenant_id
    assert entry.actor == actor
    assert entry.action == action
    assert entry.resource == resource
    mock_session.add.assert_called_once_with(entry)
    mock_session.flush.assert_called_once()

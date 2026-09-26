import os
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from config import settings
from db.models import Base, Tenant, CatalogItem, CatalogRecommendation, AccessAuditLog
from db.engine import engine, SessionLocal, auditor_engine, AuditorSessionLocal


@pytest.fixture(scope="session")
def db_engine():
    """Returns the primary database engine."""
    return engine


@pytest.fixture(scope="session")
def db_available():
    """Checks if PostgreSQL is available with a 1-second socket ping."""
    import socket
    from urllib.parse import urlparse
    parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://"))
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


@pytest.fixture(scope="function")
def db_session_factory(db_engine, db_available):
    """Ensures database tables exist before running integration tests."""
    if not db_available:
        pytest.skip("PostgreSQL (Cloud SQL/Docker) not running on port 5432. Integration RLS tests require live PostgreSQL.")

    try:
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"Database not accessible ({e}). Integration tests requiring live PostgreSQL skipped.")

    yield SessionLocal


@pytest.fixture(scope="function")
def test_tenants(db_engine):
    """
    Creates two distinct test tenants for cross-tenant isolation testing.
    Uses direct session to create tenant records (tenants table is not RLS-scoped).
    Cleans up created tenants after the test.
    """
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()

    with Session(db_engine) as session:
        tenant_a = Tenant(id=tenant_a_id, name=f"Test Tenant A - {tenant_a_id.hex[:6]}")
        tenant_b = Tenant(id=tenant_b_id, name=f"Test Tenant B - {tenant_b_id.hex[:6]}")
        session.add_all([tenant_a, tenant_b])
        session.commit()
        session.refresh(tenant_a)
        session.refresh(tenant_b)

    yield tenant_a, tenant_b

    # Cleanup
    with Session(db_engine) as session:
        session.execute(text("DELETE FROM tenants WHERE id IN (:id_a, :id_b)"), {"id_a": tenant_a_id, "id_b": tenant_b_id})
        session.commit()

import uuid
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.engine import SessionLocal, AuditorSessionLocal
from db.models import AccessAuditLog


def validate_tenant_id(tenant_id: str) -> str:
    """Validates that tenant_id is a valid UUID string to prevent injection."""
    try:
        val = uuid.UUID(str(tenant_id))
        return str(val)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"Invalid tenant_id '{tenant_id}': Must be a valid UUID string.") from exc


@contextmanager
def tenant_scoped_session(tenant_id: str) -> Generator[Session, None, None]:
    """
    The ONLY sanctioned way to get a DB session in this codebase.
    Sets the RLS session variable before any other statement runs,
    inside the same transaction, so it can never be bypassed or
    forgotten by a caller.
    """
    valid_tid = validate_tenant_id(tenant_id)
    session: Session = SessionLocal()
    try:
        # Sets RLS context variable. Parameterized query ensures complete safety.
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": valid_tid})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def auditor_scoped_session() -> Generator[Session, None, None]:
    """
    Sanctioned session for compliance and auditing.
    Connects with the restricted 'auditor_role' which only has read permissions
    on access_audit_log across tenants.
    """
    session: Session = AuditorSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def write_audit_log(
    session: Session,
    tenant_id: str,
    actor: str,
    action: str,
    resource: str,
) -> AccessAuditLog:
    """
    Writes an audit record to access_audit_log within the caller's active session.
    Enforces that tenant_id is valid and non-empty.
    """
    valid_tid = validate_tenant_id(tenant_id)
    audit_entry = AccessAuditLog(
        tenant_id=valid_tid,
        actor=actor,
        action=action,
        resource=resource,
    )
    session.add(audit_entry)
    session.flush()
    return audit_entry


def check_db_health() -> bool:
    """
    Sanctioned health-check helper located strictly inside db/session.py
    to prevent engine.connect() leaks across application handlers.
    """
    from db.engine import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


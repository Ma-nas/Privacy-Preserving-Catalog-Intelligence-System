from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

# Primary runtime engine (connects as unprivileged app_role)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=settings.DB_POOL_PRE_PING,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    future=True,
)

# Compliance auditor engine (connects as auditor_role, read-only cross-tenant access to audit log)
auditor_engine = create_engine(
    settings.AUDITOR_DATABASE_URL,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    future=True,
)

AuditorSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=auditor_engine,
    expire_on_commit=False,
    future=True,
)

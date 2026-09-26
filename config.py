import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Privacy-Preserving Catalog Intelligence System"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database settings
    # Primary application connection string (unprivileged app_role)
    DATABASE_URL: str = "postgresql+psycopg://app_user:app_password@localhost:5432/catalog_db"
    # Migration connection string (migration_role / ddl permissions)
    MIGRATION_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/catalog_db"
    # Auditor connection string (auditor_role)
    AUDITOR_DATABASE_URL: str = "postgresql+psycopg://auditor_user:auditor_password@localhost:5432/catalog_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_BROKER_DB: int = 0
    REDIS_BACKEND_DB: int = 1

    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_BROKER_DB}"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_BACKEND_DB}"

    # Rate Limiting & Concurrency Backpressure
    TENANT_MAX_CONCURRENT_TASKS: int = 10

    # Security & JWT
    JWT_SECRET_KEY: str = "dev-insecure-secret-key-change-in-prod-32bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ML Microservices endpoints (Cloud Run in production, local containers in dev)
    CLASSIFICATION_SERVICE_URL: str = "http://localhost:8001"
    DESCRIPTION_SERVICE_URL: str = "http://localhost:8002"
    USE_ML_STUBS: bool = False


settings = Settings()

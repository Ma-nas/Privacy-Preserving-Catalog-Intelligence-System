import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis

from config import settings
from api.routers import catalogs, audit, auth
from api.schemas import HealthCheckResponse
from db.session import check_db_health

# Configure Structured Logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "logger":"%(name)s", "message":"%(message)s"}',
)
logger = logging.getLogger("catalog_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Privacy-Preserving Catalog Intelligence API gateway...")
    yield
    logger.info("Shutting down API gateway...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production-grade Multi-Tenant Catalog Intelligence System enforcing strict database-level "
        "PostgreSQL Row-Level Security (RLS) isolation across asynchronous enrichment pipelines."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(catalogs.router)
app.include_router(audit.router)
app.include_router(auth.router)


@app.get("/health", response_model=HealthCheckResponse, tags=["Observability"])
def health_check():
    """Health check endpoint evaluating DB and Redis connectivity."""
    db_status = "healthy" if check_db_health() else "degraded"
    redis_status = "healthy"

    # Ping Redis
    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=1)
        r.ping()
    except Exception as e:
        redis_status = f"degraded: {str(e)[:50]}"

    overall = "healthy" if (db_status == "healthy" and redis_status == "healthy") else "degraded"

    return HealthCheckResponse(
        status=overall,
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
    )

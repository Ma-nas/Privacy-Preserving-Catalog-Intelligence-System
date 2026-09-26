import os
from celery import Celery
from kombu import Queue, Exchange
from config import settings

# Initialize Celery app
celery_app = Celery(
    "catalog_pipeline",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # Crucial for zero task loss on worker crash
    worker_prefetch_multiplier=1,  # Fair distribution among workers
    # Task routing & Queues (§6.3 Queue routing)
    task_queues=(
        Queue("classification", Exchange("classification"), routing_key="classification"),
        Queue("description", Exchange("description"), routing_key="description"),
        Queue("reindex", Exchange("reindex"), routing_key="reindex"),
        Queue("default", Exchange("default"), routing_key="default"),
    ),
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_routes={
        "tasks.enrichment.enrich_catalog_item": {"queue": "classification"},
        "tasks.enrichment.reprocess_failed_items": {"queue": "reindex"},
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["tasks"])

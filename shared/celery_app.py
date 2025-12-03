"""Celery application configuration.

Provides the Celery app instance for background task processing.
"""

from celery import Celery

from shared.config import get_settings

settings = get_settings()

# Create Celery app
app = Celery(
    "openapi_showcase",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    # Task routing
    task_routes={
        "apps.orders.tasks.*": {"queue": "orders"},
        "apps.file_processor.tasks.*": {"queue": "file_processor"},
    },
    # Default queue
    task_default_queue="default",
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "apps.auth.tasks.cleanup_expired_tokens",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-old-webhook-events": {
            "task": "apps.webhook_tester.tasks.cleanup_old_events",
            "schedule": 86400.0,  # Every day
        },
    },
)

# Auto-discover tasks from all apps
app.autodiscover_tasks(
    [
        "apps.orders.tasks",
        "apps.file_processor.tasks",
    ]
)

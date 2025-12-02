"""Orders API Celery tasks package."""

from apps.orders.tasks.webhook_tasks import process_webhook_task

__all__ = [
    "process_webhook_task",
]

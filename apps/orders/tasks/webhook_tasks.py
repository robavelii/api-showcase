"""Celery tasks for webhook processing.

Provides background task processing for webhooks with retry logic.
"""

import logging
from uuid import UUID

from celery import shared_task

from apps.orders.config import get_orders_settings
from apps.orders.services.webhook_service import get_webhook_service

logger = logging.getLogger(__name__)
settings = get_orders_settings()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def process_webhook_task(self, webhook_id: str) -> dict:
    """Process a webhook event asynchronously.

    This task processes webhook events with automatic retry on failure.
    Uses exponential backoff for retries.

    Args:
        webhook_id: UUID string of the webhook to process

    Returns:
        Processing result dictionary
    """
    webhook_service = get_webhook_service()
    webhook_uuid = UUID(webhook_id)

    try:
        logger.info(f"Processing webhook {webhook_id}, attempt {self.request.retries + 1}")

        webhook = webhook_service.get_webhook(webhook_uuid)
        if webhook is None:
            logger.error(f"Webhook {webhook_id} not found")
            return {"status": "error", "message": "Webhook not found"}

        # Process based on event type
        # This is where you would add actual business logic
        # For demo purposes, we just mark it as completed
        result = _process_webhook_event(webhook.source, webhook.event_type, webhook.payload)

        if result["success"]:
            webhook_service.mark_completed(webhook_uuid)
            logger.info(f"Webhook {webhook_id} processed successfully")
            return {"status": "completed", "webhook_id": webhook_id}
        else:
            raise Exception(result.get("error", "Processing failed"))

    except Exception as exc:
        logger.error(f"Error processing webhook {webhook_id}: {exc}")

        # Check if we've exhausted retries
        if self.request.retries >= self.max_retries:
            webhook_service.mark_failed(webhook_uuid, str(exc))
            logger.error(f"Webhook {webhook_id} failed after {self.max_retries} retries")
            return {"status": "failed", "webhook_id": webhook_id, "error": str(exc)}

        # Retry with exponential backoff
        raise self.retry(exc=exc)


def _process_webhook_event(source: str, event_type: str, payload: dict) -> dict:
    """Process a webhook event based on source and type.

    Args:
        source: Webhook source (e.g., "stripe")
        event_type: Event type
        payload: Event payload

    Returns:
        Processing result with success flag
    """
    # Handle Stripe events
    if source == "stripe":
        return _process_stripe_event(event_type, payload)

    # Unknown source - just acknowledge
    return {"success": True}


def _process_stripe_event(event_type: str, payload: dict) -> dict:
    """Process Stripe webhook events.

    Args:
        event_type: Stripe event type
        payload: Event payload

    Returns:
        Processing result
    """
    # Handle different Stripe event types
    handlers = {
        "payment_intent.succeeded": _handle_payment_succeeded,
        "payment_intent.failed": _handle_payment_failed,
        "charge.refunded": _handle_charge_refunded,
    }

    handler = handlers.get(event_type)
    if handler:
        return handler(payload)

    # Unknown event type - acknowledge but don't process
    logger.info(f"Unhandled Stripe event type: {event_type}")
    return {"success": True}


def _handle_payment_succeeded(payload: dict) -> dict:
    """Handle successful payment event."""
    logger.info(f"Payment succeeded: {payload.get('id', 'unknown')}")
    # In a real app, you would update order status here
    return {"success": True}


def _handle_payment_failed(payload: dict) -> dict:
    """Handle failed payment event."""
    logger.info(f"Payment failed: {payload.get('id', 'unknown')}")
    # In a real app, you would update order status here
    return {"success": True}


def _handle_charge_refunded(payload: dict) -> dict:
    """Handle refund event."""
    logger.info(f"Charge refunded: {payload.get('id', 'unknown')}")
    # In a real app, you would process refund here
    return {"success": True}

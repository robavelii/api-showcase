"""Webhook service for Stripe webhook handling.

Provides business logic for webhook verification and processing.
"""

import hashlib
import hmac
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from apps.orders.config import get_orders_settings
from apps.orders.models.webhook_event import WebhookEvent, WebhookStatus
from apps.orders.schemas.webhook import WebhookEventResponse
from shared.pagination.cursor import (
    PaginatedResponse,
    decode_cursor,
    encode_cursor,
)


class WebhookService:
    """Service for webhook management operations."""

    def __init__(self):
        """Initialize webhook service with in-memory storage for demo."""
        self._webhooks: dict[UUID, WebhookEvent] = {}
        self._settings = get_orders_settings()

    def verify_stripe_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str | None = None,
    ) -> bool:
        """Verify Stripe webhook signature using HMAC-SHA256.

        Args:
            payload: Raw request body bytes
            signature: Stripe-Signature header value
            secret: Webhook secret (uses config default if not provided)

        Returns:
            True if signature is valid, False otherwise
        """
        if secret is None:
            secret = self._settings.stripe_webhook_secret

        # Parse Stripe signature header
        # Format: t=timestamp,v1=signature
        try:
            elements = dict(item.split("=", 1) for item in signature.split(","))
            timestamp = elements.get("t")
            sig_v1 = elements.get("v1")

            if not timestamp or not sig_v1:
                return False

            # Check timestamp is not too old (5 minute tolerance)
            current_time = int(time.time())
            sig_time = int(timestamp)
            if abs(current_time - sig_time) > 300:
                return False

            # Compute expected signature
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            expected_sig = hmac.new(
                secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            # Compare signatures using constant-time comparison
            return hmac.compare_digest(expected_sig, sig_v1)

        except (ValueError, KeyError, UnicodeDecodeError):
            return False

    def process_webhook(
        self,
        source: str,
        event_type: str,
        payload: dict[str, Any],
        signature: str | None = None,
    ) -> WebhookEventResponse:
        """Process and store a webhook event.

        Args:
            source: Webhook source (e.g., "stripe")
            event_type: Event type (e.g., "payment_intent.succeeded")
            payload: Webhook payload
            signature: Optional signature for verification

        Returns:
            Created webhook event response
        """
        webhook = WebhookEvent(
            source=source,
            event_type=event_type,
            payload=payload,
            signature=signature,
            status=WebhookStatus.PENDING,
        )

        self._webhooks[webhook.id] = webhook

        return self._to_response(webhook)

    def list_webhooks(
        self,
        cursor: str | None = None,
        limit: int = 20,
        source: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[WebhookEventResponse]:
        """List webhook events with pagination.

        Args:
            cursor: Pagination cursor
            limit: Maximum items to return
            source: Filter by source
            status: Filter by status

        Returns:
            Paginated list of webhook events
        """
        webhooks = list(self._webhooks.values())

        # Apply filters
        if source:
            webhooks = [w for w in webhooks if w.source == source]
        if status:
            webhooks = [w for w in webhooks if w.status.value == status]

        # Sort by created_at descending
        webhooks.sort(key=lambda w: w.created_at, reverse=True)

        # Apply cursor pagination
        if cursor:
            cursor_data = decode_cursor(cursor)
            cursor_id = UUID(cursor_data.id)
            cursor_idx = None
            for idx, webhook in enumerate(webhooks):
                if webhook.id == cursor_id:
                    cursor_idx = idx
                    break
            if cursor_idx is not None:
                webhooks = webhooks[cursor_idx + 1 :]

        # Get page with one extra
        page_webhooks = webhooks[: limit + 1]
        has_more = len(page_webhooks) > limit
        page_webhooks = page_webhooks[:limit]

        # Build next cursor
        next_cursor = None
        if has_more and page_webhooks:
            last_webhook = page_webhooks[-1]
            next_cursor = encode_cursor(
                id=last_webhook.id,
                created_at=last_webhook.created_at,
            )

        items = [self._to_response(w) for w in page_webhooks]

        return PaginatedResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def retry_webhook(self, webhook_id: UUID) -> WebhookEventResponse | None:
        """Retry processing a failed webhook.

        Args:
            webhook_id: ID of the webhook to retry

        Returns:
            Updated webhook response or None if not found
        """
        webhook = self._webhooks.get(webhook_id)
        if webhook is None:
            return None

        # Reset status and increment retry count
        webhook.status = WebhookStatus.PENDING
        webhook.retry_count += 1
        webhook.error_message = None

        return self._to_response(webhook)

    def mark_completed(self, webhook_id: UUID) -> WebhookEventResponse | None:
        """Mark a webhook as completed.

        Args:
            webhook_id: ID of the webhook

        Returns:
            Updated webhook response or None if not found
        """
        webhook = self._webhooks.get(webhook_id)
        if webhook is None:
            return None

        webhook.status = WebhookStatus.COMPLETED
        webhook.processed_at = datetime.now(UTC)

        return self._to_response(webhook)

    def mark_failed(self, webhook_id: UUID, error_message: str) -> WebhookEventResponse | None:
        """Mark a webhook as failed.

        Args:
            webhook_id: ID of the webhook
            error_message: Error description

        Returns:
            Updated webhook response or None if not found
        """
        webhook = self._webhooks.get(webhook_id)
        if webhook is None:
            return None

        webhook.status = WebhookStatus.FAILED
        webhook.error_message = error_message

        return self._to_response(webhook)

    def get_webhook(self, webhook_id: UUID) -> WebhookEventResponse | None:
        """Get a webhook by ID.

        Args:
            webhook_id: Webhook ID

        Returns:
            Webhook response or None if not found
        """
        webhook = self._webhooks.get(webhook_id)
        if webhook is None:
            return None
        return self._to_response(webhook)

    def _to_response(self, webhook: WebhookEvent) -> WebhookEventResponse:
        """Convert WebhookEvent model to response schema."""
        return WebhookEventResponse(
            id=webhook.id,
            source=webhook.source,
            event_type=webhook.event_type,
            payload=webhook.payload,
            status=webhook.status.value,
            retry_count=webhook.retry_count,
            error_message=webhook.error_message,
            processed_at=webhook.processed_at,
            created_at=webhook.created_at,
        )


# Global service instance for dependency injection
_webhook_service: WebhookService | None = None


def get_webhook_service() -> WebhookService:
    """Get or create the webhook service instance."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service

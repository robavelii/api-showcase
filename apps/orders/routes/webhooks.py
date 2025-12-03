"""Webhooks API routes.

Provides endpoints for webhook management and Stripe integration.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from apps.orders.schemas.webhook import WebhookEventResponse, WebhookRetryRequest
from apps.orders.services.webhook_service import WebhookService, get_webhook_service
from apps.orders.tasks.webhook_tasks import process_webhook_task
from shared.pagination.cursor import PaginatedResponse

router = APIRouter()


@router.post(
    "/webhooks/stripe",
    response_model=WebhookEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive Stripe webhook",
    description="Endpoint for receiving Stripe webhook events.",
    responses={
        201: {
            "description": "Webhook received and queued for processing",
        },
        400: {
            "description": "Invalid signature",
        },
    },
)
async def receive_stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str, Header(alias="Stripe-Signature")],
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> WebhookEventResponse:
    """Receive and process a Stripe webhook event."""
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature
    if not webhook_service.verify_stripe_signature(body, stripe_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )

    # Parse payload
    import json

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from e

    # Extract event type
    event_type = payload.get("type", "unknown")

    # Store webhook event
    webhook = webhook_service.process_webhook(
        source="stripe",
        event_type=event_type,
        payload=payload,
        signature=stripe_signature,
    )

    # Queue for async processing
    process_webhook_task.delay(str(webhook.id))

    return webhook


@router.get(
    "/webhooks",
    response_model=PaginatedResponse[WebhookEventResponse],
    summary="List webhooks",
    description="Get a paginated list of received webhook events.",
    responses={
        200: {
            "description": "List of webhook events",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "source": "stripe",
                                "event_type": "payment_intent.succeeded",
                                "payload": {"id": "pi_123"},
                                "status": "completed",
                                "retry_count": 0,
                                "error_message": None,
                                "processed_at": "2024-01-15T10:31:00Z",
                                "created_at": "2024-01-15T10:30:00Z",
                            }
                        ],
                        "next_cursor": None,
                        "has_more": False,
                    }
                }
            },
        }
    },
)
async def list_webhooks(
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    source: Annotated[str | None, Query(description="Filter by source")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> PaginatedResponse[WebhookEventResponse]:
    """List webhook events with pagination."""
    return webhook_service.list_webhooks(
        cursor=cursor,
        limit=limit,
        source=source,
        status=status,
    )


@router.post(
    "/webhooks/retry",
    response_model=WebhookEventResponse,
    summary="Retry webhook",
    description="Retry processing a failed webhook event.",
    responses={
        200: {
            "description": "Webhook queued for retry",
        },
        404: {
            "description": "Webhook not found",
        },
    },
)
async def retry_webhook(
    data: WebhookRetryRequest,
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> WebhookEventResponse:
    """Retry processing a failed webhook."""
    webhook = webhook_service.retry_webhook(data.webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {data.webhook_id} not found",
        )

    # Queue for async processing
    process_webhook_task.delay(str(data.webhook_id))

    return webhook


@router.get(
    "/webhooks/{webhook_id}",
    response_model=WebhookEventResponse,
    summary="Get webhook",
    description="Get webhook event details by ID.",
    responses={
        200: {
            "description": "Webhook event details",
        },
        404: {
            "description": "Webhook not found",
        },
    },
)
async def get_webhook(
    webhook_id: UUID,
    webhook_service: WebhookService = Depends(get_webhook_service),
) -> WebhookEventResponse:
    """Get a webhook event by ID."""
    webhook = webhook_service.get_webhook(webhook_id)
    if webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )
    return webhook

"""Webhook request/response schemas.

Defines Pydantic schemas for webhook management endpoints.
"""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookEventResponse(BaseModel):
    """Webhook event response schema."""

    model_config = {"from_attributes": True}

    id: UUID = Field(
        ...,
        description="Webhook event ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    source: str = Field(
        ...,
        description="Webhook source (e.g., stripe)",
        json_schema_extra={"example": "stripe"},
    )
    event_type: str = Field(
        ...,
        description="Event type",
        json_schema_extra={"example": "payment_intent.succeeded"},
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Webhook payload",
    )
    status: str = Field(
        ...,
        description="Processing status",
        json_schema_extra={"example": "completed"},
    )
    retry_count: int = Field(
        ...,
        description="Number of retry attempts",
        json_schema_extra={"example": 0},
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if processing failed",
    )
    processed_at: datetime | None = Field(
        default=None,
        description="Processing completion timestamp",
    )
    created_at: datetime = Field(
        ...,
        description="Webhook receipt timestamp",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"},
    )



class WebhookRetryRequest(BaseModel):
    """Webhook retry request schema."""

    webhook_id: UUID = Field(
        ...,
        description="ID of the webhook event to retry",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )

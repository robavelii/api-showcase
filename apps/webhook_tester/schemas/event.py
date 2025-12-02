"""Webhook event request/response schemas.

Defines Pydantic schemas for webhook event endpoints.
"""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class EventResponse(BaseModel):
    """Response schema for webhook event data."""

    model_config = {"from_attributes": True}

    id: UUID = Field(
        ...,
        description="Unique event ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440002"},
    )
    bin_id: UUID = Field(
        ...,
        description="Bin ID that received this event",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    method: str = Field(
        ...,
        description="HTTP method of the request",
        json_schema_extra={"example": "POST"},
    )
    path: str = Field(
        ...,
        description="Request path",
        json_schema_extra={"example": "/"},
    )
    headers: dict[str, Any] = Field(
        ...,
        description="Request headers",
        json_schema_extra={
            "example": {
                "Content-Type": "application/json",
                "X-Webhook-Signature": "sha256=abc123",
            }
        },
    )
    body: str = Field(
        ...,
        description="Request body content",
        json_schema_extra={"example": '{"event": "payment.completed", "amount": 100}'},
    )
    content_type: str = Field(
        ...,
        description="Content-Type header value",
        json_schema_extra={"example": "application/json"},
    )
    source_ip: str = Field(
        ...,
        description="Source IP address of the request",
        json_schema_extra={"example": "192.168.1.100"},
    )
    query_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Query string parameters",
        json_schema_extra={"example": {"token": "abc123"}},
    )
    received_at: datetime = Field(
        ...,
        description="Timestamp when the event was received",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"},
    )


class EventListResponse(BaseModel):
    """Response schema for listing webhook events."""

    items: list[EventResponse] = Field(
        ...,
        description="List of webhook events",
    )
    next_cursor: str | None = Field(
        default=None,
        description="Cursor for the next page",
    )
    has_more: bool = Field(
        default=False,
        description="Whether there are more events",
    )


class ReplayEventRequest(BaseModel):
    """Request schema for replaying a webhook event."""

    target_url: str = Field(
        ...,
        description="URL to replay the webhook to",
        json_schema_extra={"example": "https://example.com/webhook"},
    )


class ReplayEventResponse(BaseModel):
    """Response schema for replay result."""

    success: bool = Field(
        ...,
        description="Whether the replay was successful",
    )
    status_code: int | None = Field(
        default=None,
        description="HTTP status code from the target",
        json_schema_extra={"example": 200},
    )
    response_body: str | None = Field(
        default=None,
        description="Response body from the target",
    )
    error: str | None = Field(
        default=None,
        description="Error message if replay failed",
    )


class WebSocketEventMessage(BaseModel):
    """WebSocket message for real-time event streaming."""

    type: str = Field(
        ...,
        description="Message type (event, ping, pong)",
        json_schema_extra={"example": "event"},
    )
    data: EventResponse | None = Field(
        default=None,
        description="Event data for event messages",
    )

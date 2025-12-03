"""Notification request/response schemas.

Defines Pydantic schemas for notification management endpoints.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SendNotificationRequest(BaseModel):
    """Request schema for sending notifications."""

    user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of user IDs to send notification to",
        json_schema_extra={"example": ["550e8400-e29b-41d4-a716-446655440000"]},
    )
    title: str = Field(
        ...,
        max_length=255,
        description="Notification title",
        json_schema_extra={"example": "New Order Received"},
    )
    message: str = Field(
        ...,
        max_length=2000,
        description="Notification message content",
        json_schema_extra={"example": "You have received a new order #12345"},
    )
    type: str = Field(
        default="info",
        description="Notification type (info, success, warning, error, system)",
        json_schema_extra={"example": "info"},
    )
    extra_data: dict[str, Any] | None = Field(
        default=None,
        description="Additional data for the notification",
        json_schema_extra={"example": {"order_id": "12345", "amount": 99.99}},
    )


class MarkAsReadRequest(BaseModel):
    """Request schema for marking notifications as read."""

    notification_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of notification IDs to mark as read",
        json_schema_extra={"example": ["550e8400-e29b-41d4-a716-446655440001"]},
    )


class NotificationResponse(BaseModel):
    """Response schema for notification data."""

    model_config = {"from_attributes": True}

    id: UUID = Field(
        ...,
        description="Notification ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440001"},
    )
    user_id: UUID = Field(
        ...,
        description="User ID who received the notification",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    title: str = Field(
        ...,
        description="Notification title",
        json_schema_extra={"example": "New Order Received"},
    )
    message: str = Field(
        ...,
        description="Notification message content",
        json_schema_extra={"example": "You have received a new order #12345"},
    )
    type: str = Field(
        ...,
        description="Notification type",
        json_schema_extra={"example": "info"},
    )
    is_read: bool = Field(
        ...,
        description="Whether the notification has been read",
        json_schema_extra={"example": False},
    )
    extra_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional data",
        json_schema_extra={"example": {"order_id": "12345"}},
    )
    created_at: datetime = Field(
        ...,
        description="Notification creation timestamp",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"},
    )


class WebSocketMessage(BaseModel):
    """WebSocket message schema."""

    type: str = Field(
        ...,
        description="Message type (notification, ping, pong, error)",
        json_schema_extra={"example": "notification"},
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Message payload",
    )


class SSEEvent(BaseModel):
    """Server-Sent Event schema."""

    event: str = Field(
        ...,
        description="Event type",
        json_schema_extra={"example": "notification"},
    )
    data: dict[str, Any] = Field(
        ...,
        description="Event data",
    )
    id: str | None = Field(
        default=None,
        description="Event ID for client reconnection",
    )
    retry: int | None = Field(
        default=None,
        description="Reconnection time in milliseconds",
    )

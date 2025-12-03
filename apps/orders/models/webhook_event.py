"""WebhookEvent SQLModel for webhook tracking.

Defines the WebhookEvent database model for tracking received webhooks.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class WebhookStatus(str, Enum):
    """Webhook processing status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WebhookEvent(SQLModel, table=True):
    """Webhook event database model."""

    __tablename__ = "webhook_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(max_length=50, index=True)  # e.g., "stripe"
    event_type: str = Field(max_length=100, index=True)  # e.g., "payment_intent.succeeded"
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    signature: str | None = Field(default=None, max_length=500)
    status: WebhookStatus = Field(default=WebhookStatus.PENDING)
    retry_count: int = Field(default=0)
    error_message: str | None = Field(default=None, max_length=1000)
    processed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(from_attributes=True)

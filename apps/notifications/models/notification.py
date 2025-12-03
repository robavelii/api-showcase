"""Notification SQLModel for real-time notifications.

Defines the Notification database model.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from shared.database.base import utc_now_naive


class NotificationType(str, Enum):
    """Notification type enumeration."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"


class Notification(SQLModel, table=True):
    """Notification database model."""

    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    title: str = Field(max_length=255)
    message: str = Field(max_length=2000)
    type: NotificationType = Field(default=NotificationType.INFO)
    is_read: bool = Field(default=False)
    extra_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now_naive)

    model_config = ConfigDict(from_attributes=True)

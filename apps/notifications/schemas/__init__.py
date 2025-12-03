"""Notifications schemas package."""

from apps.notifications.schemas.notification import (
    MarkAsReadRequest,
    NotificationResponse,
    SendNotificationRequest,
)

__all__ = [
    "NotificationResponse",
    "SendNotificationRequest",
    "MarkAsReadRequest",
]

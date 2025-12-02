"""Notifications schemas package."""

from apps.notifications.schemas.notification import (
    NotificationResponse,
    SendNotificationRequest,
    MarkAsReadRequest,
)

__all__ = [
    "NotificationResponse",
    "SendNotificationRequest",
    "MarkAsReadRequest",
]

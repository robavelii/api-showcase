"""Notification service for managing notifications.

Provides business logic for sending, retrieving, and managing notifications.
"""

from typing import Any
from uuid import UUID

from apps.notifications.models.notification import Notification, NotificationType
from apps.notifications.schemas.notification import (
    NotificationResponse,
    SendNotificationRequest,
)
from apps.notifications.services.connection_manager import ConnectionManager
from shared.pagination.cursor import (
    PaginatedResponse,
    PaginationParams,
    decode_cursor,
    encode_cursor,
)


class NotificationService:
    """Service for managing notifications."""

    def __init__(
        self,
        connection_manager: ConnectionManager | None = None,
        db_session: Any | None = None,
    ):
        """Initialize the notification service.

        Args:
            connection_manager: WebSocket connection manager for real-time delivery
            db_session: Database session for persistence
        """
        self._connection_manager = connection_manager
        self._db = db_session
        # In-memory storage for testing (replace with DB in production)
        self._notifications: dict[str, list[Notification]] = {}

    async def send_notification(
        self,
        request: SendNotificationRequest,
    ) -> list[NotificationResponse]:
        """Send a notification to specified users.

        Args:
            request: The notification request with user IDs and content

        Returns:
            List of created notification responses
        """
        notifications = []

        for user_id in request.user_ids:
            notification = Notification(
                user_id=user_id,
                title=request.title,
                message=request.message,
                type=NotificationType(request.type),
                extra_data=request.extra_data or {},
            )

            # Store notification
            user_key = str(user_id)
            if user_key not in self._notifications:
                self._notifications[user_key] = []
            self._notifications[user_key].append(notification)

            # Send via WebSocket if connected
            if self._connection_manager:
                await self._connection_manager.send_to_user(
                    user_id,
                    {
                        "type": "notification",
                        "data": NotificationResponse.model_validate(notification).model_dump(
                            mode="json"
                        ),
                    },
                )

            notifications.append(NotificationResponse.model_validate(notification))

        return notifications

    async def get_history(
        self,
        user_id: UUID,
        pagination: PaginationParams | None = None,
    ) -> PaginatedResponse[NotificationResponse]:
        """Get notification history for a user.

        Args:
            user_id: The user ID to get notifications for
            pagination: Optional pagination parameters

        Returns:
            Paginated list of notifications in reverse chronological order
        """
        if pagination is None:
            pagination = PaginationParams()

        user_key = str(user_id)
        all_notifications = self._notifications.get(user_key, [])

        # Sort by created_at descending (reverse chronological)
        sorted_notifications = sorted(all_notifications, key=lambda n: n.created_at, reverse=True)

        # Apply cursor-based pagination
        start_index = 0
        if pagination.cursor:
            try:
                cursor_data = decode_cursor(pagination.cursor)
                # Find the position after the cursor
                for i, notif in enumerate(sorted_notifications):
                    if str(notif.id) == cursor_data.id:
                        start_index = i + 1
                        break
            except ValueError:
                pass  # Invalid cursor, start from beginning

        # Get page of items (limit + 1 to check for more)
        end_index = start_index + pagination.limit + 1
        page_items = sorted_notifications[start_index:end_index]

        # Check if there are more items
        has_more = len(page_items) > pagination.limit
        if has_more:
            page_items = page_items[: pagination.limit]

        # Generate next cursor
        next_cursor = None
        if has_more and page_items:
            last_item = page_items[-1]
            next_cursor = encode_cursor(
                id=last_item.id,
                created_at=last_item.created_at,
            )

        return PaginatedResponse(
            items=[NotificationResponse.model_validate(n) for n in page_items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def mark_as_read(
        self,
        user_id: UUID,
        notification_ids: list[UUID],
    ) -> int:
        """Mark notifications as read.

        Args:
            user_id: The user ID who owns the notifications
            notification_ids: List of notification IDs to mark as read

        Returns:
            Number of notifications marked as read
        """
        user_key = str(user_id)
        notifications = self._notifications.get(user_key, [])

        count = 0
        notification_id_strs = {str(nid) for nid in notification_ids}

        for notification in notifications:
            if str(notification.id) in notification_id_strs and not notification.is_read:
                notification.is_read = True
                count += 1

        return count

    async def get_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
    ) -> NotificationResponse | None:
        """Get a specific notification.

        Args:
            user_id: The user ID who owns the notification
            notification_id: The notification ID to retrieve

        Returns:
            The notification if found, None otherwise
        """
        user_key = str(user_id)
        notifications = self._notifications.get(user_key, [])

        for notification in notifications:
            if notification.id == notification_id:
                return NotificationResponse.model_validate(notification)

        return None

    def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications for a user.

        Args:
            user_id: The user ID to count unread notifications for

        Returns:
            Number of unread notifications
        """
        user_key = str(user_id)
        notifications = self._notifications.get(user_key, [])
        return sum(1 for n in notifications if not n.is_read)

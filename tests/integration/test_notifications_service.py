"""Integration tests for the Notifications service.

Tests notification sending, retrieval, and management.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.notifications.schemas.notification import SendNotificationRequest
from apps.notifications.services.notification_service import NotificationService
from shared.pagination.cursor import PaginationParams


class TestNotificationServiceSending:
    """Tests for notification sending."""

    @pytest.fixture
    def service(self):
        """Create a fresh NotificationService instance."""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_send_notification_success(self, service):
        """Test successful notification sending."""
        user_id = uuid4()
        request = SendNotificationRequest(
            user_ids=[user_id],
            title="Test Notification",
            message="This is a test message",
            type="info",
        )

        result = await service.send_notification(request)

        assert len(result) == 1
        assert result[0].user_id == user_id
        assert result[0].title == "Test Notification"
        assert result[0].message == "This is a test message"
        assert result[0].type == "info"
        assert result[0].is_read is False

    @pytest.mark.asyncio
    async def test_send_notification_to_multiple_users(self, service):
        """Test sending notification to multiple users."""
        user_ids = [uuid4() for _ in range(5)]
        request = SendNotificationRequest(
            user_ids=user_ids,
            title="Broadcast",
            message="Message to all",
            type="warning",
        )

        result = await service.send_notification(request)

        assert len(result) == 5
        result_user_ids = {n.user_id for n in result}
        assert result_user_ids == set(user_ids)

    @pytest.mark.asyncio
    async def test_send_notification_with_extra_data(self, service):
        """Test sending notification with extra data."""
        user_id = uuid4()
        extra_data = {"order_id": "12345", "action": "view_order"}
        request = SendNotificationRequest(
            user_ids=[user_id],
            title="Order Update",
            message="Your order has shipped",
            type="success",
            extra_data=extra_data,
        )

        result = await service.send_notification(request)

        assert result[0].extra_data == extra_data

    @pytest.mark.asyncio
    async def test_send_notification_broadcasts_via_websocket(self):
        """Test that notifications are broadcast via WebSocket."""
        mock_connection_manager = AsyncMock()
        service = NotificationService(connection_manager=mock_connection_manager)

        user_id = uuid4()
        request = SendNotificationRequest(
            user_ids=[user_id],
            title="Test",
            message="Test message",
            type="info",
        )

        await service.send_notification(request)

        mock_connection_manager.send_to_user.assert_called_once()
        call_args = mock_connection_manager.send_to_user.call_args
        assert call_args[0][0] == user_id
        assert call_args[0][1]["type"] == "notification"


class TestNotificationServiceRetrieval:
    """Tests for notification retrieval."""

    @pytest.fixture
    def service(self):
        """Create a fresh NotificationService instance."""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_get_history_returns_user_notifications(self, service):
        """Test getting notification history for a user."""
        user_id = uuid4()

        for i in range(5):
            request = SendNotificationRequest(
                user_ids=[user_id],
                title=f"Notification {i}",
                message=f"Message {i}",
                type="info",
            )
            await service.send_notification(request)

        result = await service.get_history(user_id)

        assert len(result.items) == 5

    @pytest.mark.asyncio
    async def test_get_history_isolated_by_user(self, service):
        """Test that notification history is isolated by user."""
        user1 = uuid4()
        user2 = uuid4()

        for _ in range(3):
            await service.send_notification(
                SendNotificationRequest(user_ids=[user1], title="Test", message="Test", type="info")
            )
        for _ in range(2):
            await service.send_notification(
                SendNotificationRequest(user_ids=[user2], title="Test", message="Test", type="info")
            )

        result1 = await service.get_history(user1)
        result2 = await service.get_history(user2)

        assert len(result1.items) == 3
        assert len(result2.items) == 2

    @pytest.mark.asyncio
    async def test_get_history_reverse_chronological_order(self, service):
        """Test that history is in reverse chronological order."""
        user_id = uuid4()

        for i in range(5):
            await service.send_notification(
                SendNotificationRequest(
                    user_ids=[user_id],
                    title=f"Notification {i}",
                    message="Test",
                    type="info",
                )
            )

        result = await service.get_history(user_id)

        for i in range(len(result.items) - 1):
            assert result.items[i].created_at >= result.items[i + 1].created_at

    @pytest.mark.asyncio
    async def test_get_notification_by_id(self, service):
        """Test retrieving a specific notification."""
        user_id = uuid4()
        sent = await service.send_notification(
            SendNotificationRequest(
                user_ids=[user_id],
                title="Specific",
                message="Specific message",
                type="info",
            )
        )

        result = await service.get_notification(user_id, sent[0].id)

        assert result is not None
        assert result.id == sent[0].id
        assert result.title == "Specific"

    @pytest.mark.asyncio
    async def test_get_nonexistent_notification_returns_none(self, service):
        """Test retrieving non-existent notification returns None."""
        result = await service.get_notification(uuid4(), uuid4())

        assert result is None


class TestNotificationServicePagination:
    """Tests for notification pagination."""

    @pytest.fixture
    def service(self):
        """Create a fresh NotificationService instance."""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_pagination_limits_results(self, service):
        """Test that pagination limits results."""
        user_id = uuid4()

        for _ in range(25):
            await service.send_notification(
                SendNotificationRequest(
                    user_ids=[user_id], title="Test", message="Test", type="info"
                )
            )

        pagination = PaginationParams(limit=10)
        result = await service.get_history(user_id, pagination)

        assert len(result.items) == 10
        assert result.has_more is True
        assert result.next_cursor is not None

    @pytest.mark.asyncio
    async def test_pagination_cursor_continues(self, service):
        """Test that cursor pagination continues correctly."""
        user_id = uuid4()

        for _ in range(25):
            await service.send_notification(
                SendNotificationRequest(
                    user_ids=[user_id], title="Test", message="Test", type="info"
                )
            )

        first_page = await service.get_history(user_id, PaginationParams(limit=10))
        second_page = await service.get_history(
            user_id, PaginationParams(limit=10, cursor=first_page.next_cursor)
        )

        first_ids = {n.id for n in first_page.items}
        second_ids = {n.id for n in second_page.items}

        assert len(first_ids & second_ids) == 0  # No overlap


class TestNotificationServiceMarkAsRead:
    """Tests for marking notifications as read."""

    @pytest.fixture
    def service(self):
        """Create a fresh NotificationService instance."""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_mark_as_read_success(self, service):
        """Test marking notifications as read."""
        user_id = uuid4()
        sent = await service.send_notification(
            SendNotificationRequest(user_ids=[user_id], title="Test", message="Test", type="info")
        )

        count = await service.mark_as_read(user_id, [sent[0].id])

        assert count == 1

        notification = await service.get_notification(user_id, sent[0].id)
        assert notification.is_read is True

    @pytest.mark.asyncio
    async def test_mark_multiple_as_read(self, service):
        """Test marking multiple notifications as read."""
        user_id = uuid4()
        notification_ids = []

        for _ in range(5):
            sent = await service.send_notification(
                SendNotificationRequest(
                    user_ids=[user_id], title="Test", message="Test", type="info"
                )
            )
            notification_ids.append(sent[0].id)

        count = await service.mark_as_read(user_id, notification_ids[:3])

        assert count == 3

    @pytest.mark.asyncio
    async def test_mark_already_read_not_counted(self, service):
        """Test that already read notifications are not counted."""
        user_id = uuid4()
        sent = await service.send_notification(
            SendNotificationRequest(user_ids=[user_id], title="Test", message="Test", type="info")
        )

        # Mark as read twice
        count1 = await service.mark_as_read(user_id, [sent[0].id])
        count2 = await service.mark_as_read(user_id, [sent[0].id])

        assert count1 == 1
        assert count2 == 0


class TestNotificationServiceUnreadCount:
    """Tests for unread notification counting."""

    @pytest.fixture
    def service(self):
        """Create a fresh NotificationService instance."""
        return NotificationService()

    @pytest.mark.asyncio
    async def test_get_unread_count(self, service):
        """Test getting unread notification count."""
        user_id = uuid4()

        for _ in range(5):
            await service.send_notification(
                SendNotificationRequest(
                    user_ids=[user_id], title="Test", message="Test", type="info"
                )
            )

        count = service.get_unread_count(user_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_unread_count_decreases_when_read(self, service):
        """Test that unread count decreases when notifications are read."""
        user_id = uuid4()
        notification_ids = []

        for _ in range(5):
            sent = await service.send_notification(
                SendNotificationRequest(
                    user_ids=[user_id], title="Test", message="Test", type="info"
                )
            )
            notification_ids.append(sent[0].id)

        await service.mark_as_read(user_id, notification_ids[:2])
        count = service.get_unread_count(user_id)

        assert count == 3

    @pytest.mark.asyncio
    async def test_unread_count_zero_for_new_user(self, service):
        """Test that unread count is zero for user with no notifications."""
        count = service.get_unread_count(uuid4())

        assert count == 0

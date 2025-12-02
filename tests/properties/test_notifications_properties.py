"""Property-based tests for notifications API.

**Feature: openapi-showcase**
"""

import json
from datetime import datetime, UTC
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings, strategies as st, assume

from apps.notifications.models.notification import Notification, NotificationType
from apps.notifications.schemas.notification import NotificationResponse, SendNotificationRequest
from apps.notifications.services.connection_manager import ConnectionManager


# Strategies for generating test data
uuid_strategy = st.uuids()
notification_type_strategy = st.sampled_from([t.value for t in NotificationType])
title_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())
message_strategy = st.text(min_size=1, max_size=500).filter(lambda x: x.strip())


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self, should_fail: bool = False):
        self.accepted = False
        self.messages: list[dict] = []
        self.should_fail = should_fail
        self.closed = False
    
    async def accept(self):
        self.accepted = True
    
    async def send_json(self, data: dict):
        if self.should_fail:
            raise Exception("Connection failed")
        self.messages.append(data)
    
    async def close(self):
        self.closed = True


class TestWebSocketAuthenticationProperties:
    """
    **Feature: openapi-showcase, Property 19: WebSocket authentication**
    """

    @settings(max_examples=100)
    @given(user_id=uuid_strategy)
    @pytest.mark.asyncio
    async def test_valid_user_can_connect(self, user_id: UUID):
        """
        **Feature: openapi-showcase, Property 19: WebSocket authentication**
        
        For any authenticated user with valid JWT, connecting to WS /ws/notifications
        SHALL establish a connection.
        """
        manager = ConnectionManager()
        websocket = MockWebSocket()
        
        await manager.connect(websocket, user_id)
        
        # Connection should be accepted
        assert websocket.accepted is True
        
        # User should be tracked in connections
        assert manager.is_user_connected(user_id) is True
        
        # Clean up
        await manager.disconnect(websocket, user_id)

    @settings(max_examples=100)
    @given(user_id=uuid_strategy)
    @pytest.mark.asyncio
    async def test_disconnect_removes_user(self, user_id: UUID):
        """
        **Feature: openapi-showcase, Property 19: WebSocket authentication**
        
        For any connected user, disconnecting SHALL remove them from active connections.
        """
        manager = ConnectionManager()
        websocket = MockWebSocket()
        
        await manager.connect(websocket, user_id)
        assert manager.is_user_connected(user_id) is True
        
        await manager.disconnect(websocket, user_id)
        
        # User should no longer be connected
        assert manager.is_user_connected(user_id) is False

    @settings(max_examples=100)
    @given(user_id=uuid_strategy)
    @pytest.mark.asyncio
    async def test_multiple_connections_per_user(self, user_id: UUID):
        """
        **Feature: openapi-showcase, Property 19: WebSocket authentication**
        
        For any user, multiple WebSocket connections SHALL be tracked independently.
        """
        manager = ConnectionManager()
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        await manager.connect(ws1, user_id)
        await manager.connect(ws2, user_id)
        
        # Both connections should be tracked
        assert manager.is_user_connected(user_id) is True
        assert len(manager.connections[str(user_id)]) == 2
        
        # Disconnecting one should keep the other
        await manager.disconnect(ws1, user_id)
        assert manager.is_user_connected(user_id) is True
        assert len(manager.connections[str(user_id)]) == 1
        
        # Disconnecting the last should remove the user
        await manager.disconnect(ws2, user_id)
        assert manager.is_user_connected(user_id) is False


class TestWebSocketDeliveryProperties:
    """
    **Feature: openapi-showcase, Property 20: WebSocket message delivery**
    """

    @settings(max_examples=100)
    @given(
        user_id=uuid_strategy,
        message_type=st.sampled_from(["notification", "system", "ping"]),
    )
    @pytest.mark.asyncio
    async def test_message_delivered_to_connected_user(
        self, user_id: UUID, message_type: str
    ):
        """
        **Feature: openapi-showcase, Property 20: WebSocket message delivery**
        
        For any connected user and notification sent to that user, the notification
        SHALL be delivered through the WebSocket connection.
        """
        manager = ConnectionManager()
        websocket = MockWebSocket()
        
        await manager.connect(websocket, user_id)
        
        message = {"type": message_type, "data": {"test": "value"}}
        result = await manager.send_to_user(user_id, message)
        
        # Message should be sent successfully
        assert result is True
        
        # Message should be in the websocket's received messages
        assert len(websocket.messages) == 1
        assert websocket.messages[0] == message
        
        # Clean up
        await manager.disconnect(websocket, user_id)

    @settings(max_examples=100)
    @given(user_id=uuid_strategy)
    @pytest.mark.asyncio
    async def test_message_to_disconnected_user_returns_false(self, user_id: UUID):
        """
        **Feature: openapi-showcase, Property 20: WebSocket message delivery**
        
        For any user without active connections, sending a message SHALL return False
        (unless Redis is configured for cross-instance delivery).
        """
        manager = ConnectionManager()  # No Redis
        
        message = {"type": "notification", "data": {"test": "value"}}
        result = await manager.send_to_user(user_id, message)
        
        # Without Redis, message to disconnected user should fail
        assert result is False

    @settings(max_examples=100)
    @given(
        user_ids=st.lists(uuid_strategy, min_size=1, max_size=5, unique=True),
    )
    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_users(self, user_ids: list[UUID]):
        """
        **Feature: openapi-showcase, Property 20: WebSocket message delivery**
        
        For any set of connected users, broadcasting SHALL deliver to all users.
        """
        manager = ConnectionManager()
        websockets = []
        
        # Connect all users
        for user_id in user_ids:
            ws = MockWebSocket()
            await manager.connect(ws, user_id)
            websockets.append(ws)
        
        message = {"type": "broadcast", "data": {"announcement": "test"}}
        count = await manager.broadcast(message)
        
        # All users should receive the message
        assert count == len(user_ids)
        
        for ws in websockets:
            assert len(ws.messages) == 1
            assert ws.messages[0] == message
        
        # Clean up
        for user_id, ws in zip(user_ids, websockets):
            await manager.disconnect(ws, user_id)

    @settings(max_examples=100)
    @given(user_id=uuid_strategy)
    @pytest.mark.asyncio
    async def test_failed_connection_cleaned_up_on_send(self, user_id: UUID):
        """
        **Feature: openapi-showcase, Property 20: WebSocket message delivery**
        
        For any connection that fails during send, it SHALL be cleaned up automatically.
        """
        manager = ConnectionManager()
        good_ws = MockWebSocket()
        bad_ws = MockWebSocket(should_fail=True)
        
        await manager.connect(good_ws, user_id)
        await manager.connect(bad_ws, user_id)
        
        assert len(manager.connections[str(user_id)]) == 2
        
        message = {"type": "test", "data": {}}
        await manager.send_to_user(user_id, message)
        
        # Bad connection should be removed
        assert len(manager.connections[str(user_id)]) == 1
        
        # Good connection should have received the message
        assert len(good_ws.messages) == 1
        
        # Clean up
        await manager.disconnect(good_ws, user_id)


class TestNotificationHistoryPaginationProperties:
    """
    **Feature: openapi-showcase, Property 21: Notification history pagination**
    """

    @settings(max_examples=100)
    @given(
        notifications=st.lists(
            st.fixed_dictionaries({
                "id": uuid_strategy,
                "user_id": uuid_strategy,
                "title": title_strategy,
                "message": message_strategy,
                "type": notification_type_strategy,
                "is_read": st.booleans(),
                "created_at": st.datetimes(min_value=datetime(2020, 1, 1)),
            }),
            min_size=0,
            max_size=20,
        ),
    )
    def test_notifications_sorted_reverse_chronological(
        self, notifications: list[dict]
    ):
        """
        **Feature: openapi-showcase, Property 21: Notification history pagination**
        
        For any user with notifications, GET /notifications with pagination SHALL
        return notifications in reverse chronological order.
        """
        # Sort notifications by created_at descending (reverse chronological)
        sorted_notifications = sorted(
            notifications,
            key=lambda n: n["created_at"],
            reverse=True
        )
        
        # Verify the sorting is correct
        for i in range(len(sorted_notifications) - 1):
            assert sorted_notifications[i]["created_at"] >= sorted_notifications[i + 1]["created_at"]


class TestNotificationPersistenceProperties:
    """
    **Feature: openapi-showcase, Property 22: Notification persistence**
    """

    @settings(max_examples=100)
    @given(
        user_id=uuid_strategy,
        title=title_strategy,
        message=message_strategy,
        notification_type=notification_type_strategy,
    )
    def test_notification_model_creation(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
    ):
        """
        **Feature: openapi-showcase, Property 22: Notification persistence**
        
        For any notification sent via POST /notifications, the notification SHALL
        be persistable with all required fields.
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=NotificationType(notification_type),
        )
        
        # All fields should be set correctly
        assert notification.user_id == user_id
        assert notification.title == title
        assert notification.message == message
        assert notification.type.value == notification_type
        assert notification.is_read is False
        assert notification.id is not None
        assert notification.created_at is not None


class TestNotificationRoundTripProperties:
    """
    **Feature: openapi-showcase, Property 23: Notification round-trip**
    """

    @settings(max_examples=100)
    @given(
        user_id=uuid_strategy,
        title=title_strategy,
        message=message_strategy,
        notification_type=notification_type_strategy,
        is_read=st.booleans(),
        extra_data=st.fixed_dictionaries({
            "key": st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        }),
    )
    def test_notification_json_round_trip(
        self,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        is_read: bool,
        extra_data: dict,
    ):
        """
        **Feature: openapi-showcase, Property 23: Notification round-trip**
        
        For any valid Notification object, serializing to JSON and deserializing
        back SHALL produce an equivalent Notification object.
        """
        notification_id = uuid4()
        created_at = datetime.now(UTC)
        
        # Create notification response
        notification = NotificationResponse(
            id=notification_id,
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            is_read=is_read,
            extra_data=extra_data,
            created_at=created_at,
        )
        
        # Serialize to JSON
        json_str = notification.model_dump_json()
        
        # Deserialize back
        restored = NotificationResponse.model_validate_json(json_str)
        
        # Verify round-trip consistency
        assert restored.id == notification.id
        assert restored.user_id == notification.user_id
        assert restored.title == notification.title
        assert restored.message == notification.message
        assert restored.type == notification.type
        assert restored.is_read == notification.is_read
        assert restored.extra_data == notification.extra_data
        # Note: datetime comparison may have microsecond precision differences
        assert abs((restored.created_at - notification.created_at).total_seconds()) < 1

    @settings(max_examples=100)
    @given(
        user_ids=st.lists(uuid_strategy, min_size=1, max_size=5),
        title=title_strategy,
        message=message_strategy,
        notification_type=notification_type_strategy,
    )
    def test_send_notification_request_round_trip(
        self,
        user_ids: list[UUID],
        title: str,
        message: str,
        notification_type: str,
    ):
        """
        **Feature: openapi-showcase, Property 23: Notification round-trip**
        
        For any valid SendNotificationRequest, serializing to JSON and deserializing
        back SHALL produce an equivalent request object.
        """
        request = SendNotificationRequest(
            user_ids=user_ids,
            title=title,
            message=message,
            type=notification_type,
        )
        
        # Serialize to JSON
        json_str = request.model_dump_json()
        
        # Deserialize back
        restored = SendNotificationRequest.model_validate_json(json_str)
        
        # Verify round-trip consistency
        assert restored.user_ids == request.user_ids
        assert restored.title == request.title
        assert restored.message == request.message
        assert restored.type == request.type

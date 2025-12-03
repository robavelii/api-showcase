"""Integration tests for WebSocket connection manager.

Tests connection management and message broadcasting.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.notifications.services.connection_manager import ConnectionManager


class TestConnectionManagement:
    """Tests for WebSocket connection management."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager, mock_websocket):
        """Test that connect accepts the WebSocket."""
        user_id = uuid4()

        await manager.connect(mock_websocket, user_id)

        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_registers_connection(self, manager, mock_websocket):
        """Test that connect registers the connection."""
        user_id = uuid4()

        await manager.connect(mock_websocket, user_id)

        assert manager.is_user_connected(user_id)
        assert str(user_id) in manager.get_connected_users()

    @pytest.mark.asyncio
    async def test_connect_multiple_connections_per_user(self, manager):
        """Test multiple connections for same user."""
        user_id = uuid4()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, user_id)
        await manager.connect(ws2, user_id)

        assert manager.get_connection_count() == 2
        assert len(manager.connections[str(user_id)]) == 2

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_websocket):
        """Test that disconnect removes the connection."""
        user_id = uuid4()

        await manager.connect(mock_websocket, user_id)
        await manager.disconnect(mock_websocket, user_id)

        assert not manager.is_user_connected(user_id)

    @pytest.mark.asyncio
    async def test_disconnect_keeps_other_connections(self, manager):
        """Test that disconnect only removes specific connection."""
        user_id = uuid4()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, user_id)
        await manager.connect(ws2, user_id)
        await manager.disconnect(ws1, user_id)

        assert manager.is_user_connected(user_id)
        assert manager.get_connection_count() == 1


class TestMessageSending:
    """Tests for message sending functionality."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_send_to_user_success(self, manager):
        """Test sending message to a user."""
        user_id = uuid4()
        ws = AsyncMock()
        await manager.connect(ws, user_id)

        message = {"type": "notification", "data": "test"}
        result = await manager.send_to_user(user_id, message)

        assert result is True
        ws.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_user_multiple_connections(self, manager):
        """Test sending message to user with multiple connections."""
        user_id = uuid4()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, user_id)
        await manager.connect(ws2, user_id)

        message = {"type": "test"}
        await manager.send_to_user(user_id, message)

        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_disconnected_user_returns_false(self, manager):
        """Test sending to disconnected user returns False."""
        user_id = uuid4()
        message = {"type": "test"}

        result = await manager.send_to_user(user_id, message)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_handles_failed_connection(self, manager):
        """Test that failed connections are cleaned up."""
        user_id = uuid4()
        ws = AsyncMock()
        ws.send_json.side_effect = Exception("Connection closed")

        await manager.connect(ws, user_id)
        await manager.send_to_user(user_id, {"type": "test"})

        # Connection should be removed after failure
        assert not manager.is_user_connected(user_id)


class TestBroadcasting:
    """Tests for message broadcasting."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_broadcast_to_all_users(self, manager):
        """Test broadcasting to all connected users."""
        user1 = uuid4()
        user2 = uuid4()
        ws1 = AsyncMock()
        ws2 = AsyncMock()

        await manager.connect(ws1, user1)
        await manager.connect(ws2, user2)

        message = {"type": "broadcast", "data": "hello"}
        count = await manager.broadcast(message)

        assert count == 2
        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self, manager):
        """Test broadcasting with no connections."""
        message = {"type": "broadcast"}
        count = await manager.broadcast(message)

        assert count == 0

    @pytest.mark.asyncio
    async def test_broadcast_cleans_up_failed_connections(self, manager):
        """Test that broadcast cleans up failed connections."""
        user1 = uuid4()
        user2 = uuid4()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws2.send_json.side_effect = Exception("Connection closed")

        await manager.connect(ws1, user1)
        await manager.connect(ws2, user2)

        await manager.broadcast({"type": "test"})

        assert manager.is_user_connected(user1)
        assert not manager.is_user_connected(user2)


class TestConnectionQueries:
    """Tests for connection query methods."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_is_user_connected_true(self, manager):
        """Test is_user_connected returns True for connected user."""
        user_id = uuid4()
        ws = AsyncMock()

        await manager.connect(ws, user_id)

        assert manager.is_user_connected(user_id) is True

    @pytest.mark.asyncio
    async def test_is_user_connected_false(self, manager):
        """Test is_user_connected returns False for disconnected user."""
        user_id = uuid4()

        assert manager.is_user_connected(user_id) is False

    @pytest.mark.asyncio
    async def test_get_connected_users(self, manager):
        """Test getting list of connected users."""
        user1 = uuid4()
        user2 = uuid4()

        await manager.connect(AsyncMock(), user1)
        await manager.connect(AsyncMock(), user2)

        users = manager.get_connected_users()

        assert str(user1) in users
        assert str(user2) in users
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_get_connection_count(self, manager):
        """Test getting total connection count."""
        user1 = uuid4()
        user2 = uuid4()

        await manager.connect(AsyncMock(), user1)
        await manager.connect(AsyncMock(), user1)  # Same user, 2nd connection
        await manager.connect(AsyncMock(), user2)

        count = manager.get_connection_count()

        assert count == 3


class TestRedisIntegration:
    """Tests for Redis integration."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.sadd = AsyncMock()
        redis.srem = AsyncMock()
        redis.publish = AsyncMock()
        return redis

    @pytest.fixture
    def manager_with_redis(self, mock_redis):
        """Create a ConnectionManager with Redis."""
        return ConnectionManager(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_connect_registers_in_redis(self, manager_with_redis, mock_redis):
        """Test that connect registers user in Redis."""
        user_id = uuid4()
        ws = AsyncMock()

        await manager_with_redis.connect(ws, user_id)

        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_redis(self, manager_with_redis, mock_redis):
        """Test that disconnect removes user from Redis."""
        user_id = uuid4()
        ws = AsyncMock()

        await manager_with_redis.connect(ws, user_id)
        await manager_with_redis.disconnect(ws, user_id)

        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_publishes_to_redis_when_not_local(self, manager_with_redis, mock_redis):
        """Test that send publishes to Redis when user not connected locally."""
        user_id = uuid4()
        message = {"type": "test"}

        await manager_with_redis.send_to_user(user_id, message)

        mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_publishes_to_redis(self, manager_with_redis, mock_redis):
        """Test that broadcast publishes to Redis."""
        message = {"type": "broadcast"}

        await manager_with_redis.broadcast(message)

        mock_redis.publish.assert_called_once()

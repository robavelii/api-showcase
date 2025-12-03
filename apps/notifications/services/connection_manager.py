"""WebSocket connection manager for real-time notifications.

Manages WebSocket connections with Redis for multi-instance support.
"""

import json
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications.

    Supports both local connection tracking and Redis pub/sub for
    multi-instance deployments.
    """

    def __init__(self, redis_client: Any | None = None):
        """Initialize the connection manager.

        Args:
            redis_client: Optional async Redis client for multi-instance support
        """
        # Local connections: user_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        self._redis = redis_client
        self._pubsub_channel = "notifications:broadcast"

    @property
    def connections(self) -> dict[str, list[WebSocket]]:
        """Get the current connections dictionary."""
        return self._connections

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        """Accept and register a WebSocket connection.

        Args:
            websocket: The WebSocket connection to register
            user_id: The user ID associated with this connection
        """
        await websocket.accept()
        user_key = str(user_id)

        if user_key not in self._connections:
            self._connections[user_key] = []

        self._connections[user_key].append(websocket)

        # Register in Redis for multi-instance tracking
        if self._redis:
            await self._redis.sadd(f"ws:users:{user_key}", "connected")

    async def disconnect(self, websocket: WebSocket, user_id: UUID) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove
            user_id: The user ID associated with this connection
        """
        user_key = str(user_id)

        if user_key in self._connections:
            try:
                self._connections[user_key].remove(websocket)
            except ValueError:
                pass  # Connection already removed

            # Clean up empty user entries
            if not self._connections[user_key]:
                del self._connections[user_key]

                # Remove from Redis
                if self._redis:
                    await self._redis.srem(f"ws:users:{user_key}", "connected")

    async def send_to_user(self, user_id: UUID, message: dict[str, Any]) -> bool:
        """Send a message to all connections for a specific user.

        Args:
            user_id: The user ID to send the message to
            message: The message payload to send

        Returns:
            True if message was sent to at least one connection
        """
        user_key = str(user_id)
        sent = False

        # Send to local connections
        if user_key in self._connections:
            disconnected = []
            for websocket in self._connections[user_key]:
                try:
                    await websocket.send_json(message)
                    sent = True
                except Exception:
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for ws in disconnected:
                try:
                    self._connections[user_key].remove(ws)
                except ValueError:
                    pass

        # Publish to Redis for other instances
        if self._redis and not sent:
            await self._redis.publish(
                self._pubsub_channel, json.dumps({"user_id": user_key, "message": message})
            )
            sent = True

        return sent

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Broadcast a message to all connected users.

        Args:
            message: The message payload to broadcast

        Returns:
            Number of users the message was sent to
        """
        sent_count = 0
        disconnected_users = []

        for user_key, connections in self._connections.items():
            disconnected = []
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                    sent_count += 1
                except Exception:
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for ws in disconnected:
                try:
                    connections.remove(ws)
                except ValueError:
                    pass

            if not connections:
                disconnected_users.append(user_key)

        # Clean up empty user entries
        for user_key in disconnected_users:
            del self._connections[user_key]

        # Publish to Redis for other instances
        if self._redis:
            await self._redis.publish(
                self._pubsub_channel, json.dumps({"broadcast": True, "message": message})
            )

        return sent_count

    def is_user_connected(self, user_id: UUID) -> bool:
        """Check if a user has any active connections.

        Args:
            user_id: The user ID to check

        Returns:
            True if the user has at least one active connection
        """
        user_key = str(user_id)
        return user_key in self._connections and len(self._connections[user_key]) > 0

    def get_connected_users(self) -> list[str]:
        """Get list of all connected user IDs.

        Returns:
            List of user ID strings with active connections
        """
        return list(self._connections.keys())

    def get_connection_count(self) -> int:
        """Get total number of active connections.

        Returns:
            Total count of WebSocket connections
        """
        return sum(len(conns) for conns in self._connections.values())


# Global connection manager instance
_connection_manager: ConnectionManager | None = None


def get_connection_manager(redis_client: Any | None = None) -> ConnectionManager:
    """Get or create the global connection manager instance.

    Args:
        redis_client: Optional Redis client for initialization

    Returns:
        The global ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager(redis_client)
    return _connection_manager

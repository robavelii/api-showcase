"""WebSocket routes for real-time notifications.

Provides WebSocket endpoint for real-time notification delivery.
"""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
import jwt

from apps.notifications.services.connection_manager import get_connection_manager
from shared.auth.jwt import decode_token
from shared.config import get_settings

router = APIRouter()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token for authentication"),
):
    """WebSocket endpoint for real-time notifications.
    
    Connect to receive real-time notifications. Requires a valid JWT token
    passed as a query parameter.
    
    **Authentication:**
    - Pass JWT token as query parameter: `?token=<your_jwt_token>`
    
    **Message Types:**
    - `notification`: New notification received
    - `ping`: Heartbeat from server
    - `pong`: Response to client ping
    - `error`: Error message
    
    **Example Connection:**
    ```
    ws://localhost:8004/ws/notifications?token=eyJhbGciOiJIUzI1NiIs...
    ```
    """
    settings = get_settings()
    connection_manager = get_connection_manager()
    
    # Validate JWT token
    try:
        payload = decode_token(token)
        user_id = UUID(payload.sub)
    except jwt.ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
        return
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return
    
    # Accept connection and register
    await connection_manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "data": {"message": "Connected to notifications", "user_id": str(user_id)}
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            # Handle ping/pong for keepalive
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, user_id)
    except Exception:
        await connection_manager.disconnect(websocket, user_id)

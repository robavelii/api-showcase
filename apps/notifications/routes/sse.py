"""Server-Sent Events routes for notifications.

Provides SSE endpoint as a fallback for environments that don't support WebSocket.
"""

import asyncio
import json
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import jwt

from apps.notifications.config import get_notifications_settings
from apps.notifications.services.connection_manager import get_connection_manager
from shared.auth.dependencies import get_current_user_id
from shared.config import get_settings

router = APIRouter()


async def event_generator(
    request: Request,
    user_id: UUID,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a user.
    
    Args:
        request: The HTTP request
        user_id: The authenticated user's ID
        
    Yields:
        SSE formatted event strings
    """
    settings = get_notifications_settings()
    connection_manager = get_connection_manager()
    
    # Send initial connection event
    yield f"event: connected\ndata: {json.dumps({'user_id': str(user_id)})}\n\n"
    
    # Send retry timeout
    yield f"retry: {settings.sse_retry_timeout}\n\n"
    
    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break
            
            # Send heartbeat every 30 seconds
            yield f"event: heartbeat\ndata: {json.dumps({'type': 'ping'})}\n\n"
            
            # Wait before next heartbeat
            await asyncio.sleep(settings.websocket_heartbeat_interval)
            
    except asyncio.CancelledError:
        pass


@router.get(
    "/events",
    response_class=StreamingResponse,
    summary="Server-Sent Events stream",
    description="""
    Establish an SSE connection for real-time notifications.
    
    This endpoint provides a fallback for environments that don't support WebSocket.
    
    **Event Types:**
    - `connected`: Initial connection confirmation
    - `notification`: New notification received
    - `heartbeat`: Periodic keepalive ping
    
    **Example Usage:**
    ```javascript
    const eventSource = new EventSource('/api/v1/events', {
        headers: { 'Authorization': 'Bearer <token>' }
    });
    
    eventSource.addEventListener('notification', (event) => {
        const data = JSON.parse(event.data);
        console.log('New notification:', data);
    });
    ```
    """,
    responses={
        200: {
            "description": "SSE stream established",
            "content": {"text/event-stream": {}},
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
    },
)
async def sse_notifications(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
):
    """Server-Sent Events endpoint for notifications.
    
    Provides real-time notifications via SSE for clients that don't support WebSocket.
    """
    return StreamingResponse(
        event_generator(request, user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )

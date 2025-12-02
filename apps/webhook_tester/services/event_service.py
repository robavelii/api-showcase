"""Event service for managing webhook events.

Provides business logic for capturing, listing, and replaying webhook events.
"""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID

import httpx

from apps.webhook_tester.models.event import BinEvent
from apps.webhook_tester.schemas.event import EventResponse, ReplayEventResponse
from shared.pagination.cursor import (
    PaginatedResponse,
    PaginationParams,
    decode_cursor,
    encode_cursor,
)


class MockRequest:
    """Mock request object for testing."""
    
    def __init__(
        self,
        method: str = "POST",
        path: str = "/",
        headers: dict[str, str] | None = None,
        body: str = "",
        content_type: str = "application/json",
        source_ip: str = "127.0.0.1",
        query_params: dict[str, str] | None = None,
    ):
        self.method = method
        self.url = type("URL", (), {"path": path})()
        self.headers = headers or {}
        self._body = body.encode() if isinstance(body, str) else body
        self.content_type = content_type
        self.client = type("Client", (), {"host": source_ip})()
        self.query_params = query_params or {}
    
    async def body(self) -> bytes:
        return self._body


class EventService:
    """Service for managing webhook events."""

    def __init__(
        self,
        connection_manager: Any | None = None,
        db_session: Any | None = None,
    ):
        """Initialize the event service.
        
        Args:
            connection_manager: WebSocket connection manager for real-time delivery
            db_session: Database session for persistence
        """
        self._connection_manager = connection_manager
        self._db = db_session
        # In-memory storage for testing (replace with DB in production)
        self._events: dict[str, list[BinEvent]] = {}

    def _event_to_response(self, event: BinEvent) -> EventResponse:
        """Convert a BinEvent model to an EventResponse.
        
        Args:
            event: The BinEvent model
            
        Returns:
            EventResponse
        """
        return EventResponse(
            id=event.id,
            bin_id=event.bin_id,
            method=event.method,
            path=event.path,
            headers=event.headers,
            body=event.body,
            content_type=event.content_type,
            source_ip=event.source_ip,
            query_params=event.query_params,
            received_at=event.received_at,
        )

    async def capture_event(
        self,
        bin_id: UUID,
        request: Any,
    ) -> EventResponse:
        """Capture a webhook event from an incoming request.
        
        Args:
            bin_id: The bin ID to capture the event for
            request: The incoming HTTP request (FastAPI Request or MockRequest)
            
        Returns:
            The captured event response
        """
        # Extract request details
        method = request.method
        path = request.url.path if hasattr(request.url, "path") else str(request.url)
        
        # Get headers as dict
        if hasattr(request.headers, "items"):
            headers = dict(request.headers.items())
        else:
            headers = dict(request.headers)
        
        # Get body
        if hasattr(request, "body") and callable(request.body):
            body_bytes = await request.body()
            body = body_bytes.decode("utf-8", errors="replace")
        else:
            body = ""
        
        # Get content type
        content_type = headers.get("content-type", headers.get("Content-Type", ""))
        
        # Get source IP
        if hasattr(request, "client") and request.client:
            source_ip = request.client.host if hasattr(request.client, "host") else str(request.client)
        else:
            source_ip = ""
        
        # Get query params
        if hasattr(request, "query_params"):
            query_params = dict(request.query_params)
        else:
            query_params = {}
        
        # Create the event
        event = BinEvent(
            bin_id=bin_id,
            method=method,
            path=path,
            headers=headers,
            body=body,
            content_type=content_type,
            source_ip=source_ip,
            query_params=query_params,
        )
        
        # Store the event
        bin_key = str(bin_id)
        if bin_key not in self._events:
            self._events[bin_key] = []
        self._events[bin_key].append(event)
        
        event_response = self._event_to_response(event)
        
        # Broadcast to WebSocket clients
        if self._connection_manager:
            await self._connection_manager.broadcast_to_bin(
                bin_id,
                {
                    "type": "event",
                    "data": event_response.model_dump(mode="json"),
                }
            )
        
        return event_response

    async def list_events(
        self,
        bin_id: UUID,
        pagination: PaginationParams | None = None,
    ) -> PaginatedResponse[EventResponse]:
        """List events for a bin.
        
        Args:
            bin_id: The bin ID to list events for
            pagination: Optional pagination parameters
            
        Returns:
            Paginated list of events in reverse chronological order
        """
        if pagination is None:
            pagination = PaginationParams()
        
        bin_key = str(bin_id)
        all_events = self._events.get(bin_key, [])
        
        # Sort by received_at descending (reverse chronological)
        sorted_events = sorted(
            all_events,
            key=lambda e: e.received_at,
            reverse=True
        )
        
        # Apply cursor-based pagination
        start_index = 0
        if pagination.cursor:
            try:
                cursor_data = decode_cursor(pagination.cursor)
                # Find the position after the cursor
                for i, event in enumerate(sorted_events):
                    if str(event.id) == cursor_data.id:
                        start_index = i + 1
                        break
            except ValueError:
                pass  # Invalid cursor, start from beginning
        
        # Get page of items (limit + 1 to check for more)
        end_index = start_index + pagination.limit + 1
        page_items = sorted_events[start_index:end_index]
        
        # Check if there are more items
        has_more = len(page_items) > pagination.limit
        if has_more:
            page_items = page_items[:pagination.limit]
        
        # Generate next cursor
        next_cursor = None
        if has_more and page_items:
            last_item = page_items[-1]
            next_cursor = encode_cursor(
                id=last_item.id,
                created_at=last_item.received_at,
            )
        
        return PaginatedResponse(
            items=[self._event_to_response(e) for e in page_items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def get_event(
        self,
        bin_id: UUID,
        event_id: UUID,
    ) -> EventResponse | None:
        """Get a specific event.
        
        Args:
            bin_id: The bin ID the event belongs to
            event_id: The event ID to retrieve
            
        Returns:
            The event if found, None otherwise
        """
        bin_key = str(bin_id)
        events = self._events.get(bin_key, [])
        
        for event in events:
            if event.id == event_id:
                return self._event_to_response(event)
        
        return None

    async def replay_event(
        self,
        bin_id: UUID,
        event_id: UUID,
        target_url: str,
    ) -> ReplayEventResponse:
        """Replay a webhook event to a target URL.
        
        Args:
            bin_id: The bin ID the event belongs to
            event_id: The event ID to replay
            target_url: The URL to replay the event to
            
        Returns:
            The replay result
        """
        # Get the event
        event = await self.get_event(bin_id, event_id)
        if not event:
            return ReplayEventResponse(
                success=False,
                error="Event not found",
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Replay the request
                response = await client.request(
                    method=event.method,
                    url=target_url,
                    headers={k: v for k, v in event.headers.items() if k.lower() not in ["host", "content-length"]},
                    content=event.body,
                    timeout=30.0,
                )
                
                return ReplayEventResponse(
                    success=True,
                    status_code=response.status_code,
                    response_body=response.text[:1000],  # Limit response body size
                )
        except Exception as e:
            return ReplayEventResponse(
                success=False,
                error=str(e),
            )

    def get_event_count(self, bin_id: UUID) -> int:
        """Get the count of events for a bin.
        
        Args:
            bin_id: The bin ID to count events for
            
        Returns:
            Number of events in the bin
        """
        bin_key = str(bin_id)
        return len(self._events.get(bin_key, []))

    def clear_events(self, bin_id: UUID) -> int:
        """Clear all events for a bin.
        
        Args:
            bin_id: The bin ID to clear events for
            
        Returns:
            Number of events cleared
        """
        bin_key = str(bin_id)
        count = len(self._events.get(bin_key, []))
        self._events[bin_key] = []
        return count

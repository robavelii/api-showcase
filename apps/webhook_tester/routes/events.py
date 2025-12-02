"""Webhook event routes.

Provides endpoints for capturing and retrieving webhook events.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from apps.webhook_tester.schemas.event import (
    EventListResponse,
    EventResponse,
    ReplayEventRequest,
    ReplayEventResponse,
)
from apps.webhook_tester.services.bin_service import BinService
from apps.webhook_tester.services.event_service import EventService
from shared.pagination.cursor import PaginationParams

router = APIRouter()


# Dependencies
def get_bin_service() -> BinService:
    """Get the bin service instance."""
    return BinService()


def get_event_service() -> EventService:
    """Get the event service instance."""
    return EventService()


@router.post(
    "/{bin_id}",
    response_model=EventResponse,
    status_code=status.HTTP_200_OK,
    summary="Capture webhook event",
    description="Capture an incoming webhook request to the specified bin.",
    responses={
        200: {
            "description": "Event captured successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "bin_id": "550e8400-e29b-41d4-a716-446655440000",
                        "method": "POST",
                        "path": "/",
                        "headers": {
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": "sha256=abc123",
                        },
                        "body": '{"event": "payment.completed", "amount": 100}',
                        "content_type": "application/json",
                        "source_ip": "192.168.1.100",
                        "query_params": {},
                        "received_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        404: {"description": "Bin not found or inactive"},
    },
)
async def capture_event(
    bin_id: UUID,
    request: Request,
    bin_service: BinService = Depends(get_bin_service),
    event_service: EventService = Depends(get_event_service),
) -> EventResponse:
    """Capture an incoming webhook request.
    
    Captures all details of the incoming HTTP request including method,
    headers, body, and source IP. The event is stored and can be retrieved
    later for inspection.
    """
    # Check if bin exists and is active
    bin_model = await bin_service.get_bin_model(bin_id)
    if not bin_model or not bin_model.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found or inactive",
        )
    
    # Capture the event
    return await event_service.capture_event(bin_id, request)


@router.get(
    "/{bin_id}/events",
    response_model=EventListResponse,
    summary="List webhook events",
    description="List all captured webhook events for a bin.",
    responses={
        200: {
            "description": "List of events",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440002",
                                "bin_id": "550e8400-e29b-41d4-a716-446655440000",
                                "method": "POST",
                                "path": "/",
                                "headers": {"Content-Type": "application/json"},
                                "body": '{"event": "test"}',
                                "content_type": "application/json",
                                "source_ip": "192.168.1.100",
                                "query_params": {},
                                "received_at": "2024-01-15T10:30:00Z",
                            }
                        ],
                        "next_cursor": None,
                        "has_more": False,
                    }
                }
            },
        },
        404: {"description": "Bin not found"},
    },
)
async def list_events(
    bin_id: UUID,
    cursor: str | None = Query(default=None, description="Pagination cursor"),
    limit: int = Query(default=20, ge=1, le=100, description="Page size"),
    bin_service: BinService = Depends(get_bin_service),
    event_service: EventService = Depends(get_event_service),
) -> EventListResponse:
    """List all captured webhook events for a bin.
    
    Returns events in reverse chronological order (newest first).
    Supports cursor-based pagination.
    """
    # Check if bin exists
    bin_model = await bin_service.get_bin_model(bin_id)
    if not bin_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found",
        )
    
    # Get events with pagination
    pagination = PaginationParams(cursor=cursor, limit=limit)
    result = await event_service.list_events(bin_id, pagination)
    
    return EventListResponse(
        items=result.items,
        next_cursor=result.next_cursor,
        has_more=result.has_more,
    )


@router.get(
    "/{bin_id}/events/{event_id}",
    response_model=EventResponse,
    summary="Get a webhook event",
    description="Get details of a specific webhook event.",
    responses={
        200: {"description": "Event details"},
        404: {"description": "Event not found"},
    },
)
async def get_event(
    bin_id: UUID,
    event_id: UUID,
    bin_service: BinService = Depends(get_bin_service),
    event_service: EventService = Depends(get_event_service),
) -> EventResponse:
    """Get details of a specific webhook event.
    
    Returns the full details of a captured webhook event including
    headers, body, and metadata.
    """
    # Check if bin exists
    bin_model = await bin_service.get_bin_model(bin_id)
    if not bin_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found",
        )
    
    # Get the event
    event = await event_service.get_event(bin_id, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    return event


@router.post(
    "/{bin_id}/events/{event_id}/replay",
    response_model=ReplayEventResponse,
    summary="Replay a webhook event",
    description="Replay a captured webhook event to a target URL.",
    responses={
        200: {
            "description": "Replay result",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "response_body": '{"received": true}',
                        "error": None,
                    }
                }
            },
        },
        404: {"description": "Event not found"},
    },
)
async def replay_event(
    bin_id: UUID,
    event_id: UUID,
    request: ReplayEventRequest,
    bin_service: BinService = Depends(get_bin_service),
    event_service: EventService = Depends(get_event_service),
) -> ReplayEventResponse:
    """Replay a captured webhook event to a target URL.
    
    Sends the original request (method, headers, body) to the specified
    target URL and returns the response.
    """
    # Check if bin exists
    bin_model = await bin_service.get_bin_model(bin_id)
    if not bin_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found",
        )
    
    # Replay the event
    return await event_service.replay_event(bin_id, event_id, request.target_url)

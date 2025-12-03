"""Notification management routes.

Provides REST endpoints for notification CRUD operations.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.notifications.schemas.notification import (
    MarkAsReadRequest,
    NotificationResponse,
    SendNotificationRequest,
)
from apps.notifications.services.connection_manager import get_connection_manager
from apps.notifications.services.notification_service import NotificationService
from shared.auth.dependencies import get_current_user_id
from shared.pagination.cursor import PaginatedResponse, PaginationParams

router = APIRouter()
security = HTTPBearer()


def get_notification_service() -> NotificationService:
    """Get notification service instance."""
    return NotificationService(connection_manager=get_connection_manager())


@router.get(
    "/notifications",
    response_model=PaginatedResponse[NotificationResponse],
    summary="Get notification history",
    description="""
    Retrieve notification history for the authenticated user.

    Returns notifications in reverse chronological order (newest first)
    with cursor-based pagination.

    **Pagination:**
    - Use `cursor` from previous response to get next page
    - Default page size is 20, max is 100
    """,
    responses={
        200: {
            "description": "Paginated list of notifications",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440001",
                                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                                "title": "New Order Received",
                                "message": "You have received a new order #12345",
                                "type": "info",
                                "is_read": False,
                                "extra_data": {"order_id": "12345"},
                                "created_at": "2024-01-15T10:30:00Z",
                            }
                        ],
                        "next_cursor": "eyJpZCI6IjU1MGU4NDAwLi4uIiwiY3JlYXRlZF9hdCI6IjIwMjQtMDEtMTVUMTA6MzA6MDBaIn0=",
                        "has_more": True,
                    }
                }
            },
        },
        401: {"description": "Unauthorized"},
    },
)
async def get_notifications(
    user_id: UUID = Depends(get_current_user_id),
    cursor: str | None = Query(
        default=None,
        description="Pagination cursor from previous response",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of notifications to return",
    ),
    service: NotificationService = Depends(get_notification_service),
    _credentials: Annotated[HTTPAuthorizationCredentials, Security(security)] = None,
):
    """Get notification history for the authenticated user."""
    pagination = PaginationParams(cursor=cursor, limit=limit)
    return await service.get_history(user_id, pagination)


@router.post(
    "/notifications",
    response_model=list[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Send notifications",
    description="""
    Send notifications to one or more users.

    Notifications are persisted to the database and delivered in real-time
    via WebSocket to connected users.

    **Note:** This endpoint is typically used by admin users or internal services.
    """,
    responses={
        201: {
            "description": "Notifications created and sent",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "user_id": "550e8400-e29b-41d4-a716-446655440000",
                            "title": "New Order Received",
                            "message": "You have received a new order #12345",
                            "type": "info",
                            "is_read": False,
                            "extra_data": {"order_id": "12345"},
                            "created_at": "2024-01-15T10:30:00Z",
                        }
                    ]
                }
            },
        },
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
    },
)
async def send_notifications(
    request: SendNotificationRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
    _credentials: Annotated[HTTPAuthorizationCredentials, Security(security)] = None,
):
    """Send notifications to specified users."""
    return await service.send_notification(request)


@router.post(
    "/notifications/mark-read",
    status_code=status.HTTP_200_OK,
    summary="Mark notifications as read",
    description="""
    Mark one or more notifications as read.

    Only notifications owned by the authenticated user can be marked as read.
    """,
    responses={
        200: {
            "description": "Notifications marked as read",
            "content": {"application/json": {"example": {"marked_count": 3}}},
        },
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
    },
)
async def mark_notifications_read(
    request: MarkAsReadRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
    _credentials: Annotated[HTTPAuthorizationCredentials, Security(security)] = None,
):
    """Mark notifications as read."""
    count = await service.mark_as_read(user_id, request.notification_ids)
    return {"marked_count": count}


@router.get(
    "/notifications/unread-count",
    summary="Get unread notification count",
    description="Get the count of unread notifications for the authenticated user.",
    responses={
        200: {
            "description": "Unread count",
            "content": {"application/json": {"example": {"unread_count": 5}}},
        },
        401: {"description": "Unauthorized"},
    },
)
async def get_unread_count(
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
    _credentials: Annotated[HTTPAuthorizationCredentials, Security(security)] = None,
):
    """Get unread notification count."""
    count = service.get_unread_count(user_id)
    return {"unread_count": count}


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a specific notification",
    description="Retrieve a specific notification by ID.",
    responses={
        200: {"description": "Notification details"},
        401: {"description": "Unauthorized"},
        404: {"description": "Notification not found"},
    },
)
async def get_notification(
    notification_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
    _credentials: Annotated[HTTPAuthorizationCredentials, Security(security)] = None,
):
    """Get a specific notification."""
    notification = await service.get_notification(user_id, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return notification

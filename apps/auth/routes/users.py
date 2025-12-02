"""User routes.

Provides endpoints for user profile management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.schemas.user import UserResponse, UserUpdate
from apps.auth.services.user_service import UserService
from shared.auth.dependencies import CurrentUserID
from shared.database.session import get_session
from shared.schemas.common import ErrorResponse

router = APIRouter()


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(session)


@router.get(
    "/users/me",
    response_model=UserResponse,
    responses={
        200: {
            "description": "Current user profile",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        401: {
            "description": "Not authenticated",
            "model": ErrorResponse,
        },
        404: {
            "description": "User not found",
            "model": ErrorResponse,
        },
    },
    summary="Get current user",
    description="Get the profile of the currently authenticated user.",
)
async def get_current_user(
    user_id: CurrentUserID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Get current user profile.

    Returns the profile information of the authenticated user.
    Requires a valid JWT access token.
    """
    return await user_service.get_current_user(user_id)


@router.patch(
    "/users/me",
    response_model=UserResponse,
    responses={
        200: {
            "description": "User profile updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "newemail@example.com",
                        "full_name": "Jane Doe",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                    }
                }
            },
        },
        401: {
            "description": "Not authenticated",
            "model": ErrorResponse,
        },
        404: {
            "description": "User not found",
            "model": ErrorResponse,
        },
        409: {
            "description": "Email already in use",
            "model": ErrorResponse,
        },
    },
    summary="Update current user",
    description="Update the profile of the currently authenticated user.",
)
async def update_current_user(
    user_id: CurrentUserID,
    data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """Update current user profile.

    Updates the profile information of the authenticated user.
    Only provided fields will be updated.
    """
    return await user_service.update_user(user_id, data)

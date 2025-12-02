"""Authentication routes.

Provides endpoints for user registration, login, token refresh, and logout.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from apps.auth.services.auth_service import AuthService
from shared.database.session import get_session
from shared.schemas.common import ErrorResponse

router = APIRouter()
security = HTTPBearer(auto_error=False)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(session)


@router.post(
    "/auth/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "full_name": "John Doe",
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        409: {
            "description": "Email already registered",
            "model": ErrorResponse,
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
    },
    summary="Register a new user",
    description="Create a new user account and return authentication tokens.",
)
async def register(
    data: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterResponse:
    """Register a new user.

    Creates a new user account with the provided email, password, and name.
    Returns the user details along with JWT access and refresh tokens.
    """
    return await auth_service.register(data)


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "model": ErrorResponse,
        },
    },
    summary="Login user",
    description="Authenticate user with email and password.",
)
async def login(
    data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Login user.

    Authenticates the user with email and password.
    Returns JWT access token (15-minute expiry) and refresh token (7-day expiry).
    """
    return await auth_service.login(data)


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        401: {
            "description": "Invalid or expired refresh token",
            "model": ErrorResponse,
        },
    },
    summary="Refresh access token",
    description="Exchange a valid refresh token for new access and refresh tokens.",
)
async def refresh(
    data: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Refresh access token.

    Exchanges a valid refresh token for a new access token and rotates
    the refresh token. The old refresh token is invalidated.
    """
    return await auth_service.refresh(data.refresh_token)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Logout successful"},
        401: {
            "description": "Invalid token",
            "model": ErrorResponse,
        },
    },
    summary="Logout user",
    description="Invalidate the current access and refresh tokens.",
)
async def logout(
    data: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
) -> None:
    """Logout user.

    Invalidates the refresh token and adds the access token to the blocklist.
    """
    access_token = credentials.credentials if credentials else ""
    await auth_service.logout(access_token, data.refresh_token)

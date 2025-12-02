"""Authentication dependency injectors for FastAPI.

Provides dependency injection for authentication in route handlers.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.auth.jwt import TokenPayload, decode_token
from shared.config import get_settings

# Security scheme for OpenAPI documentation
security_scheme = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Exception raised for authentication failures."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
) -> TokenPayload:
    """Extract and validate JWT token from request.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is missing, invalid, or expired
    """
    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    try:
        payload = decode_token(credentials.credentials)

        # Verify it's an access token
        if payload.type != "access":
            raise AuthenticationError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


async def get_optional_token_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
) -> TokenPayload | None:
    """Extract and validate JWT token from request, returning None if not present.

    Args:
        credentials: HTTP Bearer credentials from request

    Returns:
        Decoded token payload or None if no token provided

    Raises:
        AuthenticationError: If token is present but invalid or expired
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)

        # Verify it's an access token
        if payload.type != "access":
            raise AuthenticationError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


async def get_current_user_id(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> str:
    """Get the current authenticated user's ID.

    Args:
        payload: Validated token payload

    Returns:
        User ID from the token
    """
    return payload.sub


async def get_optional_user_id(
    payload: Annotated[TokenPayload | None, Depends(get_optional_token_payload)],
) -> str | None:
    """Get the current user's ID if authenticated, None otherwise.

    Args:
        payload: Validated token payload or None

    Returns:
        User ID from the token or None
    """
    if payload is None:
        return None
    return payload.sub


# Type aliases for cleaner dependency injection
CurrentUserID = Annotated[str, Depends(get_current_user_id)]
OptionalUserID = Annotated[str | None, Depends(get_optional_user_id)]
RequiredToken = Annotated[TokenPayload, Depends(get_token_payload)]
OptionalToken = Annotated[TokenPayload | None, Depends(get_optional_token_payload)]

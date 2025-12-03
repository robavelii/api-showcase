"""Authentication dependency injectors for FastAPI.

Provides dependency injection for authentication in route handlers.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from shared.auth.jwt import TokenPayload, decode_token
from shared.config import get_settings

# Security scheme for OpenAPI documentation
security_scheme = HTTPBearer(auto_error=False)

# API Key security scheme for service-to-service auth
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


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

    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}") from e


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

    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}") from e


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


# Service-to-Service Authentication
class ServiceAuthError(HTTPException):
    """Exception raised for service-to-service authentication failures."""

    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "ApiKey"},
        )


async def verify_service_api_key(
    api_key: Annotated[str | None, Depends(api_key_scheme)],
) -> str:
    """Verify the service-to-service API key.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        ServiceAuthError: If API key is missing or invalid
    """
    if api_key is None:
        raise ServiceAuthError("Missing X-API-Key header")

    settings = get_settings()
    if api_key != settings.service_api_key:
        raise ServiceAuthError("Invalid API key")

    return api_key


async def verify_optional_service_api_key(
    api_key: Annotated[str | None, Depends(api_key_scheme)],
) -> str | None:
    """Verify the service-to-service API key if provided.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key or None if not provided

    Raises:
        ServiceAuthError: If API key is provided but invalid
    """
    if api_key is None:
        return None

    settings = get_settings()
    if api_key != settings.service_api_key:
        raise ServiceAuthError("Invalid API key")

    return api_key


async def get_user_or_service_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    api_key: Annotated[str | None, Depends(api_key_scheme)],
) -> tuple[str | None, str | None]:
    """Authenticate via either JWT token or service API key.

    Allows endpoints to accept both user authentication (JWT) and
    service-to-service authentication (API key).

    Args:
        credentials: HTTP Bearer credentials from request
        api_key: API key from X-API-Key header

    Returns:
        Tuple of (user_id, api_key) - one will be set, the other None

    Raises:
        AuthenticationError: If neither valid JWT nor valid API key provided
    """
    settings = get_settings()

    # Try API key first (service-to-service)
    if api_key is not None:
        if api_key == settings.service_api_key:
            return (None, api_key)
        raise ServiceAuthError("Invalid API key")

    # Try JWT token (user auth)
    if credentials is not None:
        try:
            payload = decode_token(credentials.credentials)
            if payload.type != "access":
                raise AuthenticationError("Invalid token type")
            return (payload.sub, None)
        except jwt.ExpiredSignatureError as e:
            raise AuthenticationError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}") from e

    raise AuthenticationError("Missing authentication - provide Bearer token or X-API-Key")


# Type aliases for service auth
ServiceAPIKey = Annotated[str, Depends(verify_service_api_key)]
OptionalServiceAPIKey = Annotated[str | None, Depends(verify_optional_service_api_key)]
UserOrServiceAuth = Annotated[tuple[str | None, str | None], Depends(get_user_or_service_auth)]

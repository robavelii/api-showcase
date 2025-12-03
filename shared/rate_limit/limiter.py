"""Rate limiting utilities using slowapi with Redis backend.

Provides rate limiting configuration and middleware for FastAPI applications.
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import FastAPI, Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from shared.config import get_settings

F = TypeVar("F", bound=Callable[..., Any])


def get_user_identifier(request: Request) -> str:
    """Get rate limit identifier from request.

    Uses user ID from JWT token if authenticated, otherwise falls back to IP address.

    Args:
        request: FastAPI request object

    Returns:
        Identifier string for rate limiting
    """
    # Try to get user ID from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fall back to IP address
    return get_remote_address(request)


def create_limiter(storage_uri: str | None = None) -> Limiter:
    """Create a rate limiter instance.

    Args:
        storage_uri: Redis URI for distributed rate limiting.
                    If None, uses in-memory storage (not suitable for production).

    Returns:
        Configured Limiter instance
    """
    settings = get_settings()

    if storage_uri is None:
        storage_uri = str(settings.redis_url)

    return Limiter(
        key_func=get_user_identifier,
        storage_uri=storage_uri,
        default_limits=[
            f"{settings.rate_limit_per_minute}/{settings.rate_limit_window_minutes}minutes"
        ],
        headers_enabled=True,
    )


# Global limiter instance (lazy initialization)
_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    """Get or create the global limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = create_limiter()
    return _limiter


def setup_rate_limiting(app: FastAPI, limiter: Limiter | None = None) -> None:
    """Configure rate limiting for a FastAPI application.

    Args:
        app: FastAPI application instance
        limiter: Optional custom limiter instance
    """
    if limiter is None:
        limiter = get_limiter()

    # Store limiter in app state
    app.state.limiter = limiter

    # Add rate limit exceeded handler
    def rate_limit_exceeded_handler(
        request: Request, exc: Exception
    ) -> Response | Awaitable[Response]:
        """Handle rate limit exceeded errors."""
        if isinstance(exc, RateLimitExceeded):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": str(exc.detail),
                    "retry_after": getattr(exc, "retry_after", None),
                },
            )
        return JSONResponse(status_code=500, content={"error": "internal_error"})

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Add middleware
    app.add_middleware(SlowAPIMiddleware)


def rate_limit(limit: str) -> Callable[[F], F]:
    """Decorator for custom rate limits on specific endpoints.

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")

    Returns:
        Decorator function

    Example:
        @app.get("/expensive")
        @rate_limit("5/minute")
        async def expensive_operation():
            ...
    """
    limiter = get_limiter()
    return limiter.limit(limit)


# Common rate limit decorators
def rate_limit_strict() -> Callable[[F], F]:
    """Apply strict rate limiting (10 requests per minute)."""
    return rate_limit("10/minute")


def rate_limit_standard() -> Callable[[F], F]:
    """Apply standard rate limiting (100 requests per 15 minutes)."""
    settings = get_settings()
    return rate_limit(
        f"{settings.rate_limit_per_minute}/{settings.rate_limit_window_minutes}minutes"
    )


def rate_limit_relaxed() -> Callable[[F], F]:
    """Apply relaxed rate limiting (1000 requests per hour)."""
    return rate_limit("1000/hour")

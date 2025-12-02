"""CORS middleware configuration.

Provides configurable CORS settings for FastAPI applications.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings


def setup_cors(app: FastAPI, origins: list[str] | None = None) -> None:
    """Configure CORS middleware for a FastAPI application.

    Args:
        app: FastAPI application instance
        origins: Optional list of allowed origins. If None, uses settings.
    """
    settings = get_settings()

    if origins is None:
        origins = settings.cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


def get_cors_origins() -> list[str]:
    """Get configured CORS origins."""
    return get_settings().cors_origins

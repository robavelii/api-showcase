"""Trusted hosts middleware configuration.

Provides protection against host header attacks.
"""

from typing import Type

from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from shared.config import get_settings


def setup_trusted_hosts(app: FastAPI, hosts: list[str] | None = None) -> None:
    """Configure trusted hosts middleware for a FastAPI application.

    Args:
        app: FastAPI application instance
        hosts: Optional list of trusted hosts. If None, uses settings.
    """
    settings = get_settings()

    if hosts is None:
        hosts = settings.trusted_hosts

    # Only add middleware if we have specific hosts configured
    # In development, we might want to allow all hosts
    if hosts and hosts != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=hosts,
        )


def get_trusted_hosts_middleware(hosts: list[str]) -> Type[TrustedHostMiddleware]:
    """Get a configured TrustedHostMiddleware class.
    
    Args:
        hosts: List of trusted hosts.
    
    Returns:
        Configured TrustedHostMiddleware class.
    """
    class ConfiguredTrustedHostMiddleware(TrustedHostMiddleware):
        def __init__(self, app):
            super().__init__(app, allowed_hosts=hosts)
    
    return ConfiguredTrustedHostMiddleware


def get_trusted_hosts() -> list[str]:
    """Get configured trusted hosts."""
    return get_settings().trusted_hosts

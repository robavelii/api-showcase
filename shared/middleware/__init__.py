"""Middleware utilities.

Provides CORS and trusted hosts middleware configuration.
"""

from shared.middleware.cors import get_cors_origins, setup_cors
from shared.middleware.trusted_hosts import get_trusted_hosts, setup_trusted_hosts

__all__ = [
    "get_cors_origins",
    "get_trusted_hosts",
    "setup_cors",
    "setup_trusted_hosts",
]

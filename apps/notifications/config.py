"""Notifications API specific configuration.

Extends base settings with notifications-specific configuration options.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificationsSettings(BaseSettings):
    """Notifications API specific settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Notifications API settings
    api_title: str = Field(default="Notifications API")
    api_description: str = Field(
        default="Real-time notifications API with WebSocket and SSE support"
    )
    api_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")

    # Pagination settings
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=500)

    # WebSocket settings
    websocket_heartbeat_interval: int = Field(default=30)  # seconds
    websocket_connection_timeout: int = Field(default=300)  # 5 minutes

    # SSE settings
    sse_retry_timeout: int = Field(default=3000)  # milliseconds


@lru_cache
def get_notifications_settings() -> NotificationsSettings:
    """Get cached notifications settings instance."""
    return NotificationsSettings()

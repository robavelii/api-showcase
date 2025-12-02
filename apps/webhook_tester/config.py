"""Webhook Tester API specific configuration.

Extends base settings with webhook tester-specific configuration options.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebhookTesterSettings(BaseSettings):
    """Webhook Tester API specific settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Webhook Tester API settings
    api_title: str = Field(default="Webhook Tester API")
    api_description: str = Field(
        default="Webhook testing API for creating bins and inspecting received webhooks"
    )
    api_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")

    # Pagination settings
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=500)

    # Bin settings
    max_bins_per_user: int = Field(default=10)
    max_events_per_bin: int = Field(default=1000)
    event_retention_days: int = Field(default=7)

    # WebSocket settings for real-time event streaming
    websocket_heartbeat_interval: int = Field(default=30)  # seconds


@lru_cache
def get_webhook_tester_settings() -> WebhookTesterSettings:
    """Get cached webhook tester settings instance."""
    return WebhookTesterSettings()

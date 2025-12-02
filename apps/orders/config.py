"""Orders API specific configuration.

Extends base settings with orders-specific configuration options.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OrdersSettings(BaseSettings):
    """Orders API specific settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Orders API settings
    api_title: str = Field(default="Orders API")
    api_description: str = Field(
        default="E-commerce order management API with webhook integrations"
    )
    api_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")

    # Pagination settings
    default_page_size: int = Field(default=20, ge=1, le=100)
    max_page_size: int = Field(default=100, ge=1, le=500)

    # Webhook settings
    stripe_webhook_secret: str = Field(default="whsec_test_secret")
    webhook_retry_max: int = Field(default=3, ge=1, le=10)
    webhook_retry_delay: int = Field(default=60, ge=1)  # seconds


@lru_cache
def get_orders_settings() -> OrdersSettings:
    """Get cached orders settings instance."""
    return OrdersSettings()

"""Gateway API configuration.

Configuration for the root API gateway.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Gateway API settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Gateway API settings
    api_title: str = Field(default="OpenAPI Showcase")
    api_description: str = Field(
        default="Combined API documentation for all OpenAPI Showcase services"
    )
    api_version: str = Field(default="1.0.0")

    # Service URLs for fetching individual OpenAPI specs
    auth_api_url: str = Field(default="http://localhost:8001")
    orders_api_url: str = Field(default="http://localhost:8002")
    file_processor_api_url: str = Field(default="http://localhost:8003")
    notifications_api_url: str = Field(default="http://localhost:8004")
    webhook_tester_api_url: str = Field(default="http://localhost:8005")


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    """Get cached gateway settings instance."""
    return GatewaySettings()

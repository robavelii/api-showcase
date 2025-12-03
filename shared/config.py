"""Base configuration with Pydantic Settings.

Provides environment variable loading with sensible defaults for local development.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="OpenAPI Showcase")
    app_env: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=True)

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/openapi_showcase"
    )
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")

    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=100, ge=1)
    rate_limit_window_minutes: int = Field(default=15, ge=1)

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: list[str] = Field(default=["*"])
    cors_allow_headers: list[str] = Field(default=["*"])

    # Trusted Hosts
    trusted_hosts: list[str] = Field(default=["localhost", "127.0.0.1"])

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # Service-to-Service Authentication
    service_api_key: str = Field(default="dev-service-api-key-change-in-production")

    # API-specific settings
    auth_api_port: int = Field(default=8001)
    orders_api_port: int = Field(default=8002)
    file_processor_api_port: int = Field(default=8003)
    notifications_api_port: int = Field(default=8004)
    webhook_tester_api_port: int = Field(default=8005)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

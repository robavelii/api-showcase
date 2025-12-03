"""Auth API specific configuration.

Extends base settings with auth-specific configuration options.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """Auth API specific settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Auth API settings
    api_title: str = Field(default="Auth API")
    api_description: str = Field(default="Authentication and user management API with JWT tokens")
    api_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")

    # Password requirements
    min_password_length: int = Field(default=8, ge=6)
    max_password_length: int = Field(default=72, le=128)
    require_uppercase: bool = Field(default=True)
    require_lowercase: bool = Field(default=True)
    require_digit: bool = Field(default=True)

    # User settings
    allow_registration: bool = Field(default=True)
    email_verification_required: bool = Field(default=False)


@lru_cache
def get_auth_settings() -> AuthSettings:
    """Get cached auth settings instance."""
    return AuthSettings()

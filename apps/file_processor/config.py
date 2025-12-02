"""File Processor API specific configuration.

Extends base settings with file processor-specific configuration options.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FileProcessorSettings(BaseSettings):
    """File Processor API specific settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # File Processor API settings
    api_title: str = Field(default="File Processor API")
    api_description: str = Field(
        default="File upload and conversion API with background processing"
    )
    api_version: str = Field(default="1.0.0")
    api_prefix: str = Field(default="/api/v1")

    # Upload settings
    max_upload_size: int = Field(default=100 * 1024 * 1024)  # 100MB
    allowed_content_types: list[str] = Field(
        default=[
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "text/plain",
            "text/csv",
            "application/json",
            "application/xml",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
    )
    
    # Storage settings
    storage_path: str = Field(default="/tmp/file_processor")
    signed_url_expiry: int = Field(default=3600)  # 1 hour in seconds

    # Conversion settings
    supported_target_formats: list[str] = Field(
        default=["pdf", "png", "jpg", "webp", "txt"]
    )
    conversion_timeout: int = Field(default=300)  # 5 minutes

    # Task retry settings
    task_retry_max: int = Field(default=3, ge=1, le=10)
    task_retry_base_delay: int = Field(default=60, ge=1)  # seconds

    # Webhook settings
    conversion_webhook_url: str | None = Field(default=None)


@lru_cache
def get_file_processor_settings() -> FileProcessorSettings:
    """Get cached file processor settings instance."""
    return FileProcessorSettings()

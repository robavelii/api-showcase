"""Conversion schemas for request/response validation.

Provides Pydantic schemas for file conversion operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.file_processor.models.conversion_job import ConversionStatus


class ConversionRequest(BaseModel):
    """Request schema for file conversion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "target_format": "png",
            }
        }
    )

    file_id: UUID = Field(..., description="ID of the file to convert")
    target_format: str = Field(
        ..., min_length=1, max_length=20, description="Target format for conversion"
    )


class ConversionJobResponse(BaseModel):
    """Response schema for conversion job."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "target_format": "png",
                "status": "processing",
                "progress": 50,
                "output_path": None,
                "error_message": None,
                "started_at": "2024-01-15T10:31:00Z",
                "completed_at": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:31:00Z",
            }
        },
    )

    id: UUID = Field(..., description="Unique job identifier")
    file_id: UUID = Field(..., description="ID of the source file")
    target_format: str = Field(..., description="Target format for conversion")
    status: ConversionStatus = Field(..., description="Current job status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    output_path: str | None = Field(None, description="Path to converted file")
    error_message: str | None = Field(None, description="Error message if failed")
    started_at: datetime | None = Field(None, description="Processing start timestamp")
    completed_at: datetime | None = Field(None, description="Processing completion timestamp")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class ConversionStatusResponse(BaseModel):
    """Response schema for conversion status check."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "progress": 75,
                "output_path": None,
                "error_message": None,
            }
        }
    )

    file_id: UUID = Field(..., description="ID of the file")
    status: ConversionStatus = Field(..., description="Current conversion status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    output_path: str | None = Field(None, description="Path to converted file if completed")
    error_message: str | None = Field(None, description="Error message if failed")


class ConversionWebhookPayload(BaseModel):
    """Webhook payload for conversion completion."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174002",
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "output_path": "/storage/converted/123e4567-e89b-12d3-a456-426614174002.png",
                "error_message": None,
                "completed_at": "2024-01-15T10:35:00Z",
            }
        }
    )

    job_id: UUID = Field(..., description="ID of the conversion job")
    file_id: UUID = Field(..., description="ID of the source file")
    status: ConversionStatus = Field(..., description="Final conversion status")
    output_path: str | None = Field(None, description="Path to converted file")
    error_message: str | None = Field(None, description="Error message if failed")
    completed_at: datetime = Field(..., description="Completion timestamp")

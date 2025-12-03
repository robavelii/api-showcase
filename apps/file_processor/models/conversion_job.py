"""ConversionJob model for file processor.

Represents file conversion jobs with status and progress tracking.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import ConfigDict
from sqlalchemy import Column, String, Text
from sqlmodel import Field

from shared.database.base import BaseModel


class ConversionStatus(str, Enum):
    """Conversion job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionJob(BaseModel, table=True):
    """ConversionJob model representing file conversion tasks.

    Attributes:
        id: Unique job identifier
        file_id: ID of the source file
        target_format: Target format for conversion
        status: Current job status
        progress: Progress percentage (0-100)
        output_path: Path to converted file
        error_message: Error message if failed
        started_at: Processing start timestamp
        completed_at: Processing completion timestamp
    """

    __tablename__ = "conversion_jobs"

    file_id: UUID = Field(foreign_key="files.id", index=True)
    target_format: str = Field(max_length=20)
    status: ConversionStatus = Field(
        default=ConversionStatus.PENDING,
        sa_column=Column(String(20), default=ConversionStatus.PENDING.value),
    )
    progress: int = Field(default=0, ge=0, le=100)
    output_path: str | None = Field(default=None, max_length=500)
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
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
        }
    )

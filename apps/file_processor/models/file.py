"""File model for file processor.

Represents uploaded files with metadata and status tracking.
"""

from datetime import datetime, UTC
from enum import Enum
from uuid import UUID

from sqlalchemy import Column, String
from sqlmodel import Field

from shared.database.base import BaseModel


class FileStatus(str, Enum):
    """File processing status."""

    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class File(BaseModel, table=True):
    """File model representing uploaded files.
    
    Attributes:
        id: Unique file identifier
        user_id: ID of the user who uploaded the file
        filename: Original filename
        content_type: MIME type of the file
        size_bytes: File size in bytes
        storage_path: Path where file is stored
        status: Current processing status
        created_at: Upload timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "files"

    user_id: UUID = Field(index=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(max_length=100)
    size_bytes: int = Field(ge=0)
    storage_path: str = Field(max_length=500)
    status: FileStatus = Field(
        default=FileStatus.PENDING,
        sa_column=Column(String(20), default=FileStatus.PENDING.value),
    )

    class Config:
        """Model configuration."""

        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "filename": "document.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024000,
                "storage_path": "/storage/files/123e4567-e89b-12d3-a456-426614174000.pdf",
                "status": "uploaded",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": None,
            }
        }

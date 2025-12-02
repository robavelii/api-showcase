"""File schemas for request/response validation.

Provides Pydantic schemas for file upload and metadata operations.
"""

from datetime import datetime, UTC
from uuid import UUID

from pydantic import BaseModel, Field

from apps.file_processor.models.file import FileStatus


class FileMetadata(BaseModel):
    """File metadata response schema."""

    id: UUID = Field(..., description="Unique file identifier")
    user_id: UUID = Field(..., description="ID of the user who uploaded the file")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., ge=0, description="File size in bytes")
    storage_path: str = Field(..., description="Storage path for the file")
    status: FileStatus = Field(..., description="Current file status")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    class Config:
        """Schema configuration."""

        from_attributes = True
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


class SignedUrlRequest(BaseModel):
    """Request schema for generating signed upload URL."""

    filename: str = Field(
        ..., min_length=1, max_length=255, description="Name of the file to upload"
    )
    content_type: str = Field(
        ..., min_length=1, max_length=100, description="MIME type of the file"
    )

    class Config:
        """Schema configuration."""

        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "content_type": "application/pdf",
            }
        }


class SignedUrlResponse(BaseModel):
    """Response schema for signed upload URL."""

    file_id: UUID = Field(..., description="ID assigned to the file")
    upload_url: str = Field(..., description="Signed URL for direct upload")
    expires_at: datetime = Field(..., description="URL expiration timestamp")

    class Config:
        """Schema configuration."""

        json_schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "upload_url": "https://storage.example.com/upload?signature=abc123",
                "expires_at": "2024-01-15T11:30:00Z",
            }
        }


class UploadResponse(BaseModel):
    """Response schema for file upload."""

    file: FileMetadata = Field(..., description="Uploaded file metadata")
    message: str = Field(default="File uploaded successfully")

    class Config:
        """Schema configuration."""

        json_schema_extra = {
            "example": {
                "file": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "123e4567-e89b-12d3-a456-426614174001",
                    "filename": "document.pdf",
                    "content_type": "application/pdf",
                    "size_bytes": 1024000,
                    "storage_path": "/storage/files/123e4567-e89b-12d3-a456-426614174000.pdf",
                    "status": "uploaded",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": None,
                },
                "message": "File uploaded successfully",
            }
        }

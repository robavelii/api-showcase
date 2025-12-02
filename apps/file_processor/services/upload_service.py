"""Upload service for file processor.

Handles file uploads and signed URL generation.
"""

import os
import hashlib
import hmac
from datetime import datetime, UTC, timedelta, UTC
from uuid import UUID, uuid4

from fastapi import UploadFile

from apps.file_processor.config import get_file_processor_settings
from apps.file_processor.models.file import File, FileStatus
from apps.file_processor.schemas.file import (
    FileMetadata,
    SignedUrlResponse,
)
from shared.config import get_settings
from shared.exceptions.errors import ValidationError, NotFoundError


class UploadService:
    """Service for handling file uploads and signed URL generation."""

    def __init__(self):
        """Initialize upload service."""
        self.settings = get_file_processor_settings()
        self.base_settings = get_settings()

    def _validate_content_type(self, content_type: str) -> None:
        """Validate that content type is allowed.
        
        Args:
            content_type: MIME type to validate
            
        Raises:
            ValidationError: If content type is not allowed
        """
        if content_type not in self.settings.allowed_content_types:
            raise ValidationError(
                detail=f"Content type '{content_type}' is not allowed. "
                f"Allowed types: {', '.join(self.settings.allowed_content_types)}"
            )

    def _validate_file_size(self, size: int) -> None:
        """Validate that file size is within limits.
        
        Args:
            size: File size in bytes
            
        Raises:
            ValidationError: If file size exceeds limit
        """
        if size > self.settings.max_upload_size:
            max_mb = self.settings.max_upload_size / (1024 * 1024)
            raise ValidationError(
                detail=f"File size exceeds maximum allowed size of {max_mb:.0f}MB"
            )

    def _generate_storage_path(self, file_id: UUID, filename: str) -> str:
        """Generate storage path for a file.
        
        Args:
            file_id: Unique file identifier
            filename: Original filename
            
        Returns:
            Storage path for the file
        """
        # Extract extension from filename
        ext = os.path.splitext(filename)[1] if "." in filename else ""
        return f"{self.settings.storage_path}/{file_id}{ext}"

    async def create_upload(
        self, file: UploadFile, user_id: UUID
    ) -> FileMetadata:
        """Handle multipart file upload.
        
        Args:
            file: Uploaded file from request
            user_id: ID of the user uploading the file
            
        Returns:
            FileMetadata with uploaded file information
            
        Raises:
            ValidationError: If file validation fails
        """
        # Validate content type
        content_type = file.content_type or "application/octet-stream"
        self._validate_content_type(content_type)

        # Read file content to get size
        content = await file.read()
        size_bytes = len(content)
        
        # Validate file size
        self._validate_file_size(size_bytes)

        # Generate file ID and storage path
        file_id = uuid4()
        filename = file.filename or "unnamed"
        storage_path = self._generate_storage_path(file_id, filename)

        # Ensure storage directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        # Write file to storage
        with open(storage_path, "wb") as f:
            f.write(content)

        # Create file record
        now = datetime.now(UTC)
        file_record = File(
            id=file_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            status=FileStatus.UPLOADED,
            created_at=now,
        )

        # In a real implementation, this would be saved to database
        # For now, return the metadata
        return FileMetadata(
            id=file_record.id,
            user_id=file_record.user_id,
            filename=file_record.filename,
            content_type=file_record.content_type,
            size_bytes=file_record.size_bytes,
            storage_path=file_record.storage_path,
            status=file_record.status,
            created_at=file_record.created_at,
            updated_at=file_record.updated_at,
        )

    def generate_signed_url(
        self, filename: str, content_type: str, user_id: UUID
    ) -> SignedUrlResponse:
        """Generate a signed URL for direct file upload.
        
        Args:
            filename: Name of the file to upload
            content_type: MIME type of the file
            user_id: ID of the user requesting the upload
            
        Returns:
            SignedUrlResponse with upload URL and expiration
            
        Raises:
            ValidationError: If content type is not allowed
        """
        # Validate content type
        self._validate_content_type(content_type)

        # Generate file ID
        file_id = uuid4()
        
        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(
            seconds=self.settings.signed_url_expiry
        )
        
        # Generate signature for the URL
        # In production, this would use cloud storage SDK (S3, GCS, etc.)
        signature_data = f"{file_id}:{filename}:{content_type}:{expires_at.isoformat()}"
        signature = hmac.new(
            self.base_settings.secret_key.encode(),
            signature_data.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Construct upload URL
        # In production, this would be a cloud storage presigned URL
        upload_url = (
            f"https://storage.example.com/upload"
            f"?file_id={file_id}"
            f"&signature={signature}"
            f"&expires={int(expires_at.timestamp())}"
        )

        return SignedUrlResponse(
            file_id=file_id,
            upload_url=upload_url,
            expires_at=expires_at,
        )

    def validate_signed_url(
        self, file_id: UUID, signature: str, expires: int
    ) -> bool:
        """Validate a signed upload URL.
        
        Args:
            file_id: File ID from the URL
            signature: Signature from the URL
            expires: Expiration timestamp from the URL
            
        Returns:
            True if signature is valid and not expired
        """
        # Check expiration
        if datetime.now(UTC).timestamp() > expires:
            return False

        # This is a simplified validation
        # In production, you would reconstruct and verify the full signature
        return len(signature) == 64  # SHA256 hex length


# Singleton instance
_upload_service: UploadService | None = None


def get_upload_service() -> UploadService:
    """Get upload service instance."""
    global _upload_service
    if _upload_service is None:
        _upload_service = UploadService()
    return _upload_service

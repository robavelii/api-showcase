"""Upload routes for file processor.

Provides endpoints for file uploads.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from apps.file_processor.schemas.file import (
    SignedUrlRequest,
    SignedUrlResponse,
    UploadResponse,
)
from apps.file_processor.services.upload_service import UploadService, get_upload_service
from shared.auth.dependencies import CurrentUserID

router = APIRouter()


@router.post(
    "/uploads",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload file",
    description="Upload a file using multipart form data.",
    responses={
        201: {
            "description": "File uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "file": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "550e8400-e29b-41d4-a716-446655440001",
                            "filename": "document.pdf",
                            "content_type": "application/pdf",
                            "size_bytes": 1024000,
                            "storage_path": "/storage/files/550e8400-e29b-41d4-a716-446655440000.pdf",
                            "status": "uploaded",
                            "created_at": "2024-01-15T10:30:00Z",
                            "updated_at": None,
                        },
                        "message": "File uploaded successfully",
                    }
                }
            },
        },
        400: {
            "description": "Invalid file type or size",
        },
    },
)
async def upload_file(
    user_id: CurrentUserID,
    file: UploadFile = File(..., description="File to upload"),
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    """Upload a file using multipart form data."""
    file_metadata = await upload_service.create_upload(file, UUID(user_id))

    return UploadResponse(
        file=file_metadata,
        message="File uploaded successfully",
    )


@router.post(
    "/uploads/signed-url",
    response_model=SignedUrlResponse,
    summary="Generate signed upload URL",
    description="Generate a signed URL for direct file upload.",
    responses={
        200: {
            "description": "Signed URL generated",
            "content": {
                "application/json": {
                    "example": {
                        "file_id": "550e8400-e29b-41d4-a716-446655440000",
                        "upload_url": "https://storage.example.com/upload?signature=abc123",
                        "expires_at": "2024-01-15T11:30:00Z",
                    }
                }
            },
        },
        400: {
            "description": "Invalid content type",
        },
    },
)
async def generate_signed_url(
    data: SignedUrlRequest,
    user_id: CurrentUserID,
    upload_service: UploadService = Depends(get_upload_service),
) -> SignedUrlResponse:
    """Generate a signed URL for direct file upload."""
    return upload_service.generate_signed_url(
        data.filename,
        data.content_type,
        UUID(user_id),
    )

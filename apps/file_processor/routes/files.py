"""File routes for file processor.

Provides endpoints for file conversion and status.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.file_processor.schemas.conversion import (
    ConversionJobResponse,
    ConversionRequest,
    ConversionStatusResponse,
)
from apps.file_processor.services.conversion_service import (
    ConversionService,
    get_conversion_service,
)
from shared.exceptions.errors import NotFoundError, ValidationError

router = APIRouter()


@router.post(
    "/files/convert",
    response_model=ConversionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Convert file",
    description="Queue a file conversion job.",
    responses={
        202: {
            "description": "Conversion job queued",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440002",
                        "file_id": "550e8400-e29b-41d4-a716-446655440000",
                        "target_format": "png",
                        "status": "pending",
                        "progress": 0,
                        "output_path": None,
                        "error_message": None,
                        "started_at": None,
                        "completed_at": None,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": None,
                    }
                }
            },
        },
        400: {
            "description": "Invalid target format",
        },
        404: {
            "description": "File not found",
        },
    },
)
async def convert_file(
    data: ConversionRequest,
    conversion_service: ConversionService = Depends(get_conversion_service),
) -> ConversionJobResponse:
    """Queue a file conversion job."""
    try:
        return conversion_service.queue_conversion(data.file_id, data.target_format)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.detail),
        ) from None
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail),
        ) from None


@router.get(
    "/files/{file_id}/status",
    response_model=ConversionStatusResponse,
    summary="Get conversion status",
    description="Get the current conversion status for a file.",
    responses={
        200: {
            "description": "Conversion status",
            "content": {
                "application/json": {
                    "example": {
                        "file_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "processing",
                        "progress": 75,
                        "output_path": None,
                        "error_message": None,
                    }
                }
            },
        },
        404: {
            "description": "No conversion job found for file",
        },
    },
)
async def get_conversion_status(
    file_id: UUID,
    conversion_service: ConversionService = Depends(get_conversion_service),
) -> ConversionStatusResponse:
    """Get the current conversion status for a file."""
    try:
        return conversion_service.get_status(file_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.detail),
        ) from None

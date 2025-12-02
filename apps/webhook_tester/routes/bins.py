"""Webhook bin routes.

Provides endpoints for creating, listing, and managing webhook bins.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from apps.webhook_tester.schemas.bin import (
    BinListResponse,
    BinResponse,
    CreateBinRequest,
)
from apps.webhook_tester.services.bin_service import BinService

router = APIRouter()


# Dependency to get bin service
def get_bin_service() -> BinService:
    """Get the bin service instance."""
    return BinService()


# Mock user ID for demo (in production, use auth dependency)
def get_current_user_id() -> UUID:
    """Get the current user ID from auth context."""
    # In production, this would extract user ID from JWT token
    from uuid import uuid4
    return uuid4()


@router.post(
    "/bins",
    response_model=BinResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook bin",
    description="Create a new webhook bin for capturing webhook events.",
    responses={
        201: {
            "description": "Bin created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "Stripe Webhooks Test",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                        "url": "https://api.example.com/550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
    },
)
async def create_bin(
    request: CreateBinRequest | None = None,
    service: BinService = Depends(get_bin_service),
    user_id: UUID = Depends(get_current_user_id),
) -> BinResponse:
    """Create a new webhook bin.
    
    Creates a new webhook bin that can receive and store webhook events.
    The bin URL can be used as a webhook endpoint for testing.
    """
    return await service.create_bin(user_id, request)


@router.get(
    "/bins",
    response_model=BinListResponse,
    summary="List webhook bins",
    description="List all webhook bins owned by the current user.",
    responses={
        200: {
            "description": "List of bins",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                                "name": "Stripe Webhooks Test",
                                "is_active": True,
                                "created_at": "2024-01-15T10:30:00Z",
                                "url": "https://api.example.com/550e8400-e29b-41d4-a716-446655440000",
                            }
                        ],
                        "total": 1,
                    }
                }
            },
        },
    },
)
async def list_bins(
    service: BinService = Depends(get_bin_service),
    user_id: UUID = Depends(get_current_user_id),
) -> BinListResponse:
    """List all webhook bins owned by the current user.
    
    Returns a list of all webhook bins created by the authenticated user.
    """
    bins = await service.list_bins(user_id)
    return BinListResponse(items=bins, total=len(bins))


@router.get(
    "/bins/{bin_id}",
    response_model=BinResponse,
    summary="Get a webhook bin",
    description="Get details of a specific webhook bin.",
    responses={
        200: {"description": "Bin details"},
        404: {"description": "Bin not found"},
    },
)
async def get_bin(
    bin_id: UUID,
    service: BinService = Depends(get_bin_service),
    user_id: UUID = Depends(get_current_user_id),
) -> BinResponse:
    """Get details of a specific webhook bin.
    
    Returns the details of a webhook bin if it exists and is owned by the user.
    """
    bin_response = await service.get_bin(bin_id)
    if not bin_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found",
        )
    
    # Check ownership
    if bin_response.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found",
        )
    
    return bin_response


@router.delete(
    "/bins/{bin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook bin",
    description="Delete a webhook bin and all its captured events.",
    responses={
        204: {"description": "Bin deleted successfully"},
        404: {"description": "Bin not found"},
    },
)
async def delete_bin(
    bin_id: UUID,
    service: BinService = Depends(get_bin_service),
    user_id: UUID = Depends(get_current_user_id),
) -> None:
    """Delete a webhook bin.
    
    Deletes a webhook bin and all its captured events.
    Only the owner can delete a bin.
    """
    deleted = await service.delete_bin(bin_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bin not found",
        )

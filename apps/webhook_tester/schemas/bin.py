"""Webhook bin request/response schemas.

Defines Pydantic schemas for webhook bin management endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateBinRequest(BaseModel):
    """Request schema for creating a webhook bin."""

    name: str = Field(
        default="",
        max_length=255,
        description="Optional name for the webhook bin",
        json_schema_extra={"example": "Stripe Webhooks Test"},
    )


class BinResponse(BaseModel):
    """Response schema for webhook bin data."""

    model_config = {"from_attributes": True}

    id: UUID = Field(
        ...,
        description="Unique bin ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    user_id: UUID = Field(
        ...,
        description="Owner user ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440001"},
    )
    name: str = Field(
        ...,
        description="Bin name",
        json_schema_extra={"example": "Stripe Webhooks Test"},
    )
    is_active: bool = Field(
        ...,
        description="Whether the bin is active and accepting events",
        json_schema_extra={"example": True},
    )
    created_at: datetime = Field(
        ...,
        description="Bin creation timestamp",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"},
    )
    url: str = Field(
        ...,
        description="URL to send webhooks to this bin",
        json_schema_extra={
            "example": "https://api.example.com/550e8400-e29b-41d4-a716-446655440000"
        },
    )


class BinListResponse(BaseModel):
    """Response schema for listing webhook bins."""

    items: list[BinResponse] = Field(
        ...,
        description="List of webhook bins",
    )
    total: int = Field(
        ...,
        description="Total number of bins",
        json_schema_extra={"example": 5},
    )

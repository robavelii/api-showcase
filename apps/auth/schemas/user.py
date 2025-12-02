"""User request/response schemas.

Defines Pydantic schemas for user management endpoints.
"""

from datetime import datetime, UTC
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID = Field(
        ...,
        description="User ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    email: EmailStr = Field(
        ...,
        description="User email address",
        json_schema_extra={"example": "user@example.com"},
    )
    full_name: str = Field(
        ...,
        description="User's full name",
        json_schema_extra={"example": "John Doe"},
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active",
        json_schema_extra={"example": True},
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"},
    )

    class Config:
        """Model configuration."""

        from_attributes = True


class UserUpdate(BaseModel):
    """User update request schema."""

    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="User's full name",
        json_schema_extra={"example": "Jane Doe"},
    )
    email: EmailStr | None = Field(
        default=None,
        description="User email address",
        json_schema_extra={"example": "newemail@example.com"},
    )

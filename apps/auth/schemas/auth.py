"""Authentication request/response schemas.

Defines Pydantic schemas for authentication endpoints.
"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request schema."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        json_schema_extra={"example": "user@example.com"},
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="User password (8-72 characters, must contain uppercase, lowercase, and digit)",
        json_schema_extra={"example": "SecurePass123"},
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="User's full name",
        json_schema_extra={"example": "John Doe"},
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """User login request schema."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        json_schema_extra={"example": "user@example.com"},
    )
    password: str = Field(
        ...,
        description="User password",
        json_schema_extra={"example": "SecurePass123"},
    )


class RefreshRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(
        ...,
        description="Refresh token to exchange for new tokens",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )


class LogoutRequest(BaseModel):
    """Logout request schema."""

    refresh_token: str = Field(
        ...,
        description="Refresh token to invalidate",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str = Field(
        ...,
        description="JWT access token",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
        json_schema_extra={"example": "bearer"},
    )


class RegisterResponse(BaseModel):
    """Registration response schema."""

    id: str = Field(
        ...,
        description="User ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    email: str = Field(
        ...,
        description="User email",
        json_schema_extra={"example": "user@example.com"},
    )
    full_name: str = Field(
        ...,
        description="User's full name",
        json_schema_extra={"example": "John Doe"},
    )
    access_token: str = Field(
        ...,
        description="JWT access token",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        json_schema_extra={"example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    )
    token_type: str = Field(
        default="bearer",
        description="Token type",
        json_schema_extra={"example": "bearer"},
    )

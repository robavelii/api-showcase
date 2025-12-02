"""Common response schemas used across all APIs.

This module defines shared Pydantic models for consistent API responses.
"""

from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, Field


class ValidationErrorDetail(BaseModel):
    """Schema for individual validation error details."""
    
    field: str = Field(..., description="The field that failed validation")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")


class ErrorResponse(BaseModel):
    """Standard error response schema for all API errors.
    
    This schema ensures consistent error responses across all endpoints,
    making it easier for clients to handle errors uniformly.
    """
    
    detail: str = Field(..., description="Human-readable error message")
    status_code: int = Field(..., description="HTTP status code")
    error_code: str | None = Field(
        default=None, description="Machine-readable error code"
    )
    errors: list[ValidationErrorDetail] | None = Field(
        default=None, description="List of validation errors (for 422 responses)"
    )
    timestamp: datetime = Field(..., description="When the error occurred")
    request_id: str = Field(..., description="Unique identifier for the request")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "The requested resource was not found",
                    "status_code": 404,
                    "error_code": "NOT_FOUND",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                },
                {
                    "detail": "Validation failed",
                    "status_code": 422,
                    "error_code": "VALIDATION_ERROR",
                    "errors": [
                        {
                            "field": "email",
                            "message": "Invalid email format",
                            "code": "value_error",
                        }
                    ],
                    "timestamp": "2024-01-15T10:30:00Z",
                    "request_id": "550e8400-e29b-41d4-a716-446655440001",
                },
            ]
        }
    }


class SuccessResponse(BaseModel):
    """Generic success response for operations without specific return data."""
    
    message: str = Field(..., description="Success message")
    success: bool = Field(default=True, description="Indicates operation success")

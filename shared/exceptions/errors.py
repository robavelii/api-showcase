"""Custom exception classes for the application.

This module defines a hierarchy of exceptions that map to HTTP status codes
and provide consistent error handling across all APIs.
"""

from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""
    
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    detail: str = "An unexpected error occurred"
    
    def __init__(
        self,
        detail: str | None = None,
        error_code: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.error_code = error_code or self.__class__.error_code
        self.errors = errors
        super().__init__(self.detail)


class AuthenticationError(AppException):
    """Raised when authentication fails."""
    
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    detail = "Authentication failed"


class AuthorizationError(AppException):
    """Raised when user lacks required permissions."""
    
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    detail = "You do not have permission to perform this action"


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""
    
    status_code = 404
    error_code = "NOT_FOUND"
    detail = "The requested resource was not found"


class ValidationError(AppException):
    """Raised when input validation fails."""
    
    status_code = 422
    error_code = "VALIDATION_ERROR"
    detail = "Validation failed"


class RateLimitError(AppException):
    """Raised when rate limit is exceeded."""
    
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    detail = "Too many requests. Please try again later"


class ConflictError(AppException):
    """Raised when there is a resource conflict."""
    
    status_code = 409
    error_code = "CONFLICT"
    detail = "Resource conflict occurred"


class BadRequestError(AppException):
    """Raised for malformed or invalid requests."""
    
    status_code = 400
    error_code = "BAD_REQUEST"
    detail = "Bad request"


class ServiceUnavailableError(AppException):
    """Raised when a required service is unavailable."""
    
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    detail = "Service temporarily unavailable"

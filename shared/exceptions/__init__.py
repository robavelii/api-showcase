# Exception handling utilities

from shared.exceptions.errors import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from shared.exceptions.handlers import (
    app_exception_handler,
    create_error_response,
    generic_exception_handler,
    http_exception_handler,
    register_exception_handlers,
    validation_exception_handler,
)

__all__ = [
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "BadRequestError",
    "ConflictError",
    "NotFoundError",
    "RateLimitError",
    "ServiceUnavailableError",
    "ValidationError",
    # Handlers
    "app_exception_handler",
    "create_error_response",
    "generic_exception_handler",
    "http_exception_handler",
    "register_exception_handlers",
    "validation_exception_handler",
]

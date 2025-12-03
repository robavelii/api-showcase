"""Integration tests for exception handling.

Tests custom exceptions and exception handlers.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

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
)


class TestCustomExceptions:
    """Tests for custom exception classes."""

    def test_app_exception_defaults(self):
        """Test AppException default values."""
        exc = AppException()

        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.detail == "An unexpected error occurred"
        assert exc.errors is None

    def test_app_exception_custom_values(self):
        """Test AppException with custom values."""
        exc = AppException(
            detail="Custom error",
            error_code="CUSTOM_ERROR",
            errors=[{"field": "test", "message": "error"}],
        )

        assert exc.detail == "Custom error"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.errors == [{"field": "test", "message": "error"}]

    def test_authentication_error(self):
        """Test AuthenticationError defaults."""
        exc = AuthenticationError()

        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"

    def test_authorization_error(self):
        """Test AuthorizationError defaults."""
        exc = AuthorizationError()

        assert exc.status_code == 403
        assert exc.error_code == "AUTHORIZATION_ERROR"

    def test_not_found_error(self):
        """Test NotFoundError defaults."""
        exc = NotFoundError()

        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"

    def test_validation_error(self):
        """Test ValidationError defaults."""
        exc = ValidationError()

        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"

    def test_rate_limit_error(self):
        """Test RateLimitError defaults."""
        exc = RateLimitError()

        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"

    def test_conflict_error(self):
        """Test ConflictError defaults."""
        exc = ConflictError()

        assert exc.status_code == 409
        assert exc.error_code == "CONFLICT"

    def test_bad_request_error(self):
        """Test BadRequestError defaults."""
        exc = BadRequestError()

        assert exc.status_code == 400
        assert exc.error_code == "BAD_REQUEST"

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError defaults."""
        exc = ServiceUnavailableError()

        assert exc.status_code == 503
        assert exc.error_code == "SERVICE_UNAVAILABLE"

    def test_exception_with_custom_detail(self):
        """Test exception with custom detail message."""
        exc = NotFoundError(detail="User not found")

        assert exc.detail == "User not found"
        assert exc.status_code == 404


class TestErrorResponseCreation:
    """Tests for error response creation."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response(
            status_code=404,
            detail="Not found",
        )

        assert response["status_code"] == 404
        assert response["detail"] == "Not found"
        assert "timestamp" in response
        assert "request_id" in response

    def test_create_error_response_with_error_code(self):
        """Test error response with error code."""
        response = create_error_response(
            status_code=400,
            detail="Bad request",
            error_code="INVALID_INPUT",
        )

        assert response["error_code"] == "INVALID_INPUT"

    def test_create_error_response_with_errors(self):
        """Test error response with validation errors."""
        errors = [
            {"field": "email", "message": "Invalid email format"},
            {"field": "password", "message": "Too short"},
        ]
        response = create_error_response(
            status_code=422,
            detail="Validation failed",
            errors=errors,
        )

        assert response["errors"] == errors

    def test_create_error_response_with_request_id(self):
        """Test error response with custom request ID."""
        request_id = str(uuid4())
        response = create_error_response(
            status_code=500,
            detail="Error",
            request_id=request_id,
        )

        assert response["request_id"] == request_id


class TestExceptionHandlers:
    """Tests for exception handlers."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock()
        request.state = MagicMock()
        request.state.request_id = str(uuid4())
        return request

    @pytest.mark.asyncio
    async def test_app_exception_handler(self, mock_request):
        """Test handler for AppException."""
        exc = NotFoundError(detail="Resource not found")

        response = await app_exception_handler(mock_request, exc)

        assert response.status_code == 404
        body = response.body.decode()
        assert "Resource not found" in body
        assert "NOT_FOUND" in body

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test handler for HTTP exceptions."""
        exc = StarletteHTTPException(status_code=403, detail="Forbidden")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 403
        body = response.body.decode()
        assert "Forbidden" in body

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self, mock_request):
        """Test handler for generic exceptions."""
        exc = Exception("Unexpected error")

        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500
        body = response.body.decode()
        assert "unexpected error" in body.lower()
        assert "INTERNAL_ERROR" in body


class TestExceptionHandlerRegistration:
    """Tests for exception handler registration."""

    def test_register_exception_handlers(self):
        """Test that exception handlers are registered correctly."""
        app = FastAPI()
        register_exception_handlers(app)

        # Verify handlers are registered
        assert AppException in app.exception_handlers
        assert StarletteHTTPException in app.exception_handlers
        assert Exception in app.exception_handlers

    def test_registered_handlers_work(self):
        """Test that registered handlers work in a real app."""
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/not-found")
        async def raise_not_found():
            raise NotFoundError(detail="Item not found")

        @app.get("/auth-error")
        async def raise_auth_error():
            raise AuthenticationError(detail="Invalid token")

        client = TestClient(app)

        # Test NotFoundError
        response = client.get("/not-found")
        assert response.status_code == 404
        assert "Item not found" in response.text

        # Test AuthenticationError
        response = client.get("/auth-error")
        assert response.status_code == 401
        assert "Invalid token" in response.text

    def test_validation_error_handler_formats_errors(self):
        """Test that validation errors are formatted correctly."""
        from pydantic import BaseModel

        app = FastAPI()
        register_exception_handlers(app)

        class TestModel(BaseModel):
            email: str
            age: int

        @app.post("/validate")
        async def validate_input(data: TestModel):
            return data

        client = TestClient(app)

        response = client.post("/validate", json={"email": 123, "age": "not-a-number"})
        assert response.status_code == 422
        data = response.json()
        assert "errors" in data
        assert len(data["errors"]) > 0

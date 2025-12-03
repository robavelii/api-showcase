"""Property-based tests for error response format consistency.

**Feature: openapi-showcase, Property 35: Consistent error response format**
"""

from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

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
from shared.exceptions.handlers import create_error_response

# Strategy for valid HTTP status codes
status_code_strategy = st.sampled_from([400, 401, 403, 404, 409, 422, 429, 500, 503])

# Strategy for error details (non-empty strings)
detail_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())

# Strategy for error codes (alphanumeric with underscores)
error_code_strategy = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_",
    min_size=3,
    max_size=30,
).filter(lambda x: x.strip() and not x.startswith("_") and not x.endswith("_"))

# Strategy for request IDs (UUID-like strings)
request_id_strategy = st.uuids().map(str)

# Strategy for validation error fields
validation_error_strategy = st.lists(
    st.fixed_dictionaries(
        {
            "field": st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            "message": st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
            "code": st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        }
    ),
    min_size=0,
    max_size=5,
)

# All exception classes to test
exception_classes = [
    AppException,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
]


class TestErrorResponseFormatProperties:
    """
    **Feature: openapi-showcase, Property 35: Consistent error response format**
    """

    @settings(max_examples=100)
    @given(
        status_code=status_code_strategy,
        detail=detail_strategy,
        error_code=error_code_strategy,
        request_id=request_id_strategy,
    )
    def test_error_response_contains_required_fields(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        request_id: str,
    ):
        """
        **Feature: openapi-showcase, Property 35: Consistent error response format**

        For any error raised by the application, the error response SHALL follow
        a consistent JSON structure with "detail", "status_code", and "timestamp".
        """
        response = create_error_response(
            status_code=status_code,
            detail=detail,
            error_code=error_code,
            request_id=request_id,
        )

        # Required fields must be present
        assert "detail" in response
        assert "status_code" in response
        assert "timestamp" in response
        assert "request_id" in response

        # Values must match inputs
        assert response["detail"] == detail
        assert response["status_code"] == status_code
        assert response["request_id"] == request_id

        # error_code should be present when provided
        assert "error_code" in response
        assert response["error_code"] == error_code

        # timestamp should be a valid ISO format string
        timestamp = response["timestamp"]
        assert isinstance(timestamp, str)
        # Should be parseable as datetime
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    @settings(max_examples=100)
    @given(
        status_code=status_code_strategy,
        detail=detail_strategy,
        errors=validation_error_strategy,
        request_id=request_id_strategy,
    )
    def test_error_response_with_validation_errors(
        self,
        status_code: int,
        detail: str,
        errors: list,
        request_id: str,
    ):
        """
        **Feature: openapi-showcase, Property 35: Consistent error response format**

        For any validation error, the response SHALL include an optional "errors" array
        with field-level error details.
        """
        response = create_error_response(
            status_code=status_code,
            detail=detail,
            errors=errors if errors else None,
            request_id=request_id,
        )

        # Required fields must be present
        assert "detail" in response
        assert "status_code" in response
        assert "timestamp" in response
        assert "request_id" in response

        # errors should only be present if provided and non-empty
        if errors:
            assert "errors" in response
            assert response["errors"] == errors
            # Each error should have field, message, code
            for error in response["errors"]:
                assert "field" in error
                assert "message" in error
                assert "code" in error
        else:
            assert "errors" not in response

    @settings(max_examples=50)
    @given(
        exception_class=st.sampled_from(exception_classes),
        custom_detail=st.one_of(st.none(), detail_strategy),
    )
    def test_exception_classes_have_consistent_attributes(
        self,
        exception_class: type,
        custom_detail: str | None,
    ):
        """
        **Feature: openapi-showcase, Property 35: Consistent error response format**

        For any exception class, it SHALL have status_code, error_code, and detail
        attributes that can be used to create consistent error responses.
        """
        # Create exception with optional custom detail
        if custom_detail:
            exc = exception_class(detail=custom_detail)
        else:
            exc = exception_class()

        # All exceptions must have these attributes
        assert hasattr(exc, "status_code")
        assert hasattr(exc, "error_code")
        assert hasattr(exc, "detail")

        # status_code must be a valid HTTP error code
        assert isinstance(exc.status_code, int)
        assert 400 <= exc.status_code < 600

        # error_code must be a non-empty string
        assert isinstance(exc.error_code, str)
        assert len(exc.error_code) > 0

        # detail must be a non-empty string
        assert isinstance(exc.detail, str)
        assert len(exc.detail) > 0

        # If custom detail was provided, it should be used
        if custom_detail:
            assert exc.detail == custom_detail

    @settings(max_examples=100)
    @given(
        status_code=status_code_strategy,
        detail=detail_strategy,
    )
    def test_error_response_without_optional_fields(
        self,
        status_code: int,
        detail: str,
    ):
        """
        **Feature: openapi-showcase, Property 35: Consistent error response format**

        For any error response created without optional fields, the response SHALL
        still contain all required fields and generate a request_id automatically.
        """
        response = create_error_response(
            status_code=status_code,
            detail=detail,
        )

        # Required fields must be present
        assert "detail" in response
        assert "status_code" in response
        assert "timestamp" in response
        assert "request_id" in response

        # Values must match inputs
        assert response["detail"] == detail
        assert response["status_code"] == status_code

        # request_id should be auto-generated (UUID format)
        assert isinstance(response["request_id"], str)
        assert len(response["request_id"]) == 36  # UUID string length

        # Optional fields should not be present when not provided
        assert "error_code" not in response
        assert "errors" not in response

    @settings(max_examples=50)
    @given(exception_class=st.sampled_from(exception_classes))
    def test_exception_to_error_response_consistency(
        self,
        exception_class: type,
    ):
        """
        **Feature: openapi-showcase, Property 35: Consistent error response format**

        For any exception class, creating an error response from its attributes
        SHALL produce a valid, consistent error response.
        """
        exc = exception_class()

        response = create_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
        )

        # Response should match exception attributes
        assert response["status_code"] == exc.status_code
        assert response["detail"] == exc.detail
        assert response["error_code"] == exc.error_code

        # Required fields must be present
        assert "timestamp" in response
        assert "request_id" in response

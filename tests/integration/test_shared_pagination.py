"""Integration tests for cursor-based pagination.

Tests pagination utilities including cursor encoding/decoding.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from shared.pagination.cursor import (
    CursorData,
    PaginatedResponse,
    PaginationParams,
    decode_cursor,
    encode_cursor,
)


class TestCursorEncoding:
    """Tests for cursor encoding."""

    def test_encode_cursor_basic(self):
        """Test basic cursor encoding."""
        item_id = uuid4()
        created_at = datetime.now(UTC)

        cursor = encode_cursor(id=item_id, created_at=created_at)

        assert cursor is not None
        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_encode_cursor_with_field_and_value(self):
        """Test cursor encoding with additional field and value."""
        item_id = uuid4()
        created_at = datetime.now(UTC)

        cursor = encode_cursor(
            id=item_id,
            created_at=created_at,
            field="total_amount",
            value="100.00",
        )

        assert cursor is not None

    def test_encode_cursor_is_url_safe(self):
        """Test that encoded cursor is URL-safe."""
        cursor = encode_cursor(id=uuid4(), created_at=datetime.now(UTC))

        # URL-safe base64 should not contain +, /, or =
        # (though = padding is sometimes present)
        assert "+" not in cursor
        assert "/" not in cursor


class TestCursorDecoding:
    """Tests for cursor decoding."""

    def test_decode_cursor_basic(self):
        """Test basic cursor decoding."""
        item_id = uuid4()
        created_at = datetime.now(UTC)
        cursor = encode_cursor(id=item_id, created_at=created_at)

        result = decode_cursor(cursor)

        assert isinstance(result, CursorData)
        assert result.id == str(item_id)

    def test_decode_cursor_with_field_and_value(self):
        """Test cursor decoding with field and value."""
        item_id = uuid4()
        created_at = datetime.now(UTC)
        cursor = encode_cursor(
            id=item_id,
            created_at=created_at,
            field="status",
            value="pending",
        )

        result = decode_cursor(cursor)

        assert result.field == "status"
        assert result.value == "pending"

    def test_decode_invalid_cursor_raises_error(self):
        """Test that decoding invalid cursor raises ValueError."""
        with pytest.raises(ValueError):
            decode_cursor("invalid-cursor-data")

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding produces consistent results."""
        item_id = uuid4()
        created_at = datetime.now(UTC)

        cursor = encode_cursor(id=item_id, created_at=created_at)
        result = decode_cursor(cursor)

        assert result.id == str(item_id)


class TestPaginationParams:
    """Tests for PaginationParams model."""

    def test_pagination_params_defaults(self):
        """Test PaginationParams default values."""
        params = PaginationParams()

        assert params.cursor is None
        assert params.limit == 20

    def test_pagination_params_custom_values(self):
        """Test PaginationParams with custom values."""
        params = PaginationParams(cursor="abc123", limit=50)

        assert params.cursor == "abc123"
        assert params.limit == 50


class TestPaginatedResponse:
    """Tests for PaginatedResponse model."""

    def test_paginated_response_creation(self):
        """Test creating a PaginatedResponse."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]

        response = PaginatedResponse(
            items=items,
            next_cursor="cursor123",
            has_more=True,
        )

        assert response.items == items
        assert response.next_cursor == "cursor123"
        assert response.has_more is True

    def test_paginated_response_no_more_items(self):
        """Test PaginatedResponse when no more items."""
        items = [{"id": 1}]

        response = PaginatedResponse(
            items=items,
            next_cursor=None,
            has_more=False,
        )

        assert response.next_cursor is None
        assert response.has_more is False

    def test_paginated_response_empty(self):
        """Test PaginatedResponse with empty items."""
        response = PaginatedResponse(
            items=[],
            next_cursor=None,
            has_more=False,
        )

        assert len(response.items) == 0
        assert response.has_more is False


class TestCursorData:
    """Tests for CursorData model."""

    def test_cursor_data_creation(self):
        """Test creating a CursorData instance."""
        data = CursorData(
            id="123",
            created_at="2024-01-01T00:00:00Z",
            field="status",
            value="active",
        )

        assert data.id == "123"
        assert data.created_at == "2024-01-01T00:00:00Z"
        assert data.field == "status"
        assert data.value == "active"

    def test_cursor_data_optional_fields(self):
        """Test CursorData with optional fields."""
        data = CursorData(
            id="123",
            created_at="2024-01-01T00:00:00Z",
        )

        assert data.field is None
        assert data.value is None


class TestPaginationIntegration:
    """Integration tests for pagination workflow."""

    def test_pagination_workflow(self):
        """Test complete pagination workflow."""
        # Simulate a list of items
        all_items = [{"id": i, "name": f"Item {i}"} for i in range(25)]

        # First page
        page_size = 10
        first_page_items = all_items[:page_size]
        has_more = len(all_items) > page_size

        if has_more and first_page_items:
            last_item = first_page_items[-1]
            next_cursor = encode_cursor(
                id=last_item["id"],
                created_at=datetime.now(UTC),
            )
        else:
            next_cursor = None

        first_page = PaginatedResponse(
            items=first_page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

        assert len(first_page.items) == 10
        assert first_page.has_more is True
        assert first_page.next_cursor is not None

        # Decode cursor for next page
        cursor_data = decode_cursor(first_page.next_cursor)
        assert cursor_data.id == "9"  # Last item ID from first page

    def test_pagination_last_page(self):
        """Test pagination on last page."""
        all_items = [{"id": i} for i in range(5)]

        response = PaginatedResponse(
            items=all_items,
            next_cursor=None,
            has_more=False,
        )

        assert len(response.items) == 5
        assert response.has_more is False
        assert response.next_cursor is None

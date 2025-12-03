"""Property-based tests for pagination utilities.

**Feature: openapi-showcase**
"""

from datetime import datetime
from uuid import uuid4

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from shared.pagination.cursor import (
    decode_cursor,
    encode_cursor,
    paginate_items,
)

# Strategies for generating test data
uuid_strategy = st.uuids()
datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2030, 12, 31),
)


class TestCursorPaginationProperties:
    """
    **Feature: openapi-showcase, Property 7: Cursor pagination consistency**
    """

    @settings(max_examples=100)
    @given(
        item_id=uuid_strategy,
        created_at=datetime_strategy,
    )
    def test_cursor_encode_decode_roundtrip(self, item_id, created_at):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        For any valid cursor data, encoding and then decoding SHALL produce
        equivalent cursor data.
        """
        # Encode cursor
        cursor = encode_cursor(
            id=item_id,
            created_at=created_at,
        )

        # Decode cursor
        decoded = decode_cursor(cursor)

        # Verify roundtrip
        assert decoded.id == str(item_id)
        assert decoded.created_at == created_at.isoformat()

    @settings(max_examples=100)
    @given(
        item_id=uuid_strategy,
        field=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"),
        value=st.one_of(
            st.integers(),
            st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz"),
        ),
    )
    def test_cursor_with_custom_field_roundtrip(self, item_id, field, value):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        For any cursor with custom sort field, encoding and decoding SHALL
        preserve the field name and value.
        """
        cursor = encode_cursor(
            id=item_id,
            field=field,
            value=value,
        )

        decoded = decode_cursor(cursor)

        assert decoded.id == str(item_id)
        assert decoded.field == field
        assert decoded.value == value

    @settings(max_examples=50)
    @given(
        num_items=st.integers(min_value=0, max_value=50),
        limit=st.integers(min_value=1, max_value=20),
    )
    def test_pagination_returns_correct_page_size(self, num_items, limit):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        For any list of items and limit, paginate_items SHALL return
        at most 'limit' items.
        """
        # Create test items
        items = [{"id": str(uuid4()), "name": f"item_{i}"} for i in range(num_items)]

        # Paginate
        result = paginate_items(items, limit=limit, id_field="id", created_at_field=None)

        # Verify page size
        assert len(result.items) <= limit
        assert len(result.items) == min(num_items, limit)

    @settings(max_examples=50)
    @given(
        num_items=st.integers(min_value=0, max_value=50),
        limit=st.integers(min_value=1, max_value=20),
    )
    def test_pagination_has_more_flag_correctness(self, num_items, limit):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        For any list of items, has_more SHALL be True if and only if
        there are more items than the limit.
        """
        # Create test items (add 1 extra to simulate DB query pattern)
        items = [{"id": str(uuid4()), "name": f"item_{i}"} for i in range(num_items)]

        # Paginate
        result = paginate_items(items, limit=limit, id_field="id", created_at_field=None)

        # Verify has_more flag
        expected_has_more = num_items > limit
        assert result.has_more == expected_has_more

    @settings(max_examples=50)
    @given(
        num_items=st.integers(min_value=2, max_value=30),
        limit=st.integers(min_value=1, max_value=10),
    )
    def test_pagination_cursor_present_when_has_more(self, num_items, limit):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        When has_more is True, next_cursor SHALL be present and decodable.
        """
        assume(num_items > limit)  # Ensure we have more items than limit

        # Create test items
        items = [{"id": str(uuid4()), "name": f"item_{i}"} for i in range(num_items)]

        # Paginate
        result = paginate_items(items, limit=limit, id_field="id", created_at_field=None)

        # Verify cursor is present and valid
        assert result.has_more is True
        assert result.next_cursor is not None

        # Cursor should be decodable
        decoded = decode_cursor(result.next_cursor)
        assert decoded.id is not None

    @settings(max_examples=30)
    @given(num_items=st.integers(min_value=1, max_value=20))
    def test_pagination_no_cursor_when_no_more_items(self, num_items):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        When has_more is False, next_cursor SHALL be None.
        """
        limit = num_items + 10  # Ensure limit is larger than items

        # Create test items
        items = [{"id": str(uuid4()), "name": f"item_{i}"} for i in range(num_items)]

        # Paginate
        result = paginate_items(items, limit=limit, id_field="id", created_at_field=None)

        # Verify no cursor when no more items
        assert result.has_more is False
        assert result.next_cursor is None

    def test_invalid_cursor_raises_error(self):
        """
        **Feature: openapi-showcase, Property 7: Cursor pagination consistency**

        Invalid cursor strings SHALL raise ValueError.
        """
        with pytest.raises(ValueError):
            decode_cursor("invalid-cursor-string")

        with pytest.raises(ValueError):
            decode_cursor("")

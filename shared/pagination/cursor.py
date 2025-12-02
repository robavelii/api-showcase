"""Cursor-based pagination utilities.

Provides encode/decode functions for cursor pagination and response schemas.
"""

import base64
import json
from datetime import datetime, UTC
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class CursorData(BaseModel):
    """Internal cursor data structure."""

    id: str
    created_at: str | None = None
    field: str | None = None
    value: Any = None


def encode_cursor(
    id: str | UUID,
    created_at: datetime | None = None,
    field: str | None = None,
    value: Any = None,
) -> str:
    """Encode pagination cursor data into a base64 string.

    Args:
        id: The ID of the last item
        created_at: Optional timestamp for time-based ordering
        field: Optional field name for custom sorting
        value: Optional field value for custom sorting

    Returns:
        Base64-encoded cursor string
    """
    cursor_data = {
        "id": str(id),
    }

    if created_at is not None:
        cursor_data["created_at"] = created_at.isoformat()

    if field is not None:
        cursor_data["field"] = field

    if value is not None:
        # Handle special types
        if isinstance(value, datetime):
            cursor_data["value"] = value.isoformat()
        elif isinstance(value, UUID):
            cursor_data["value"] = str(value)
        else:
            cursor_data["value"] = value

    json_str = json.dumps(cursor_data, sort_keys=True)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> CursorData:
    """Decode a base64 cursor string into cursor data.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Decoded cursor data

    Raises:
        ValueError: If cursor is invalid or malformed
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)
        return CursorData(**data)
    except Exception as e:
        raise ValueError(f"Invalid cursor: {str(e)}")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    items: list[T] = Field(description="List of items in the current page")
    next_cursor: str | None = Field(
        default=None,
        description="Cursor for the next page, null if no more pages",
    )
    has_more: bool = Field(
        default=False,
        description="Whether there are more items after this page",
    )
    total: int | None = Field(
        default=None,
        description="Total count of items (optional, may be expensive to compute)",
    )


class PaginationParams(BaseModel):
    """Pagination request parameters."""

    cursor: str | None = Field(
        default=None,
        description="Cursor from previous response for pagination",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    )


def paginate_items(
    items: list[T],
    limit: int,
    id_field: str = "id",
    created_at_field: str | None = "created_at",
    sort_field: str | None = None,
) -> PaginatedResponse[T]:
    """Create a paginated response from a list of items.

    Args:
        items: List of items (should be limit + 1 to detect has_more)
        limit: Requested page size
        id_field: Name of the ID field on items
        created_at_field: Name of the created_at field (optional)
        sort_field: Name of custom sort field (optional)

    Returns:
        PaginatedResponse with items, cursor, and has_more flag
    """
    has_more = len(items) > limit
    page_items = items[:limit]

    next_cursor = None
    if has_more and page_items:
        last_item = page_items[-1]

        # Get ID from item (handle both dict and object)
        if isinstance(last_item, dict):
            item_id = last_item.get(id_field)
            created_at = last_item.get(created_at_field) if created_at_field else None
            sort_value = last_item.get(sort_field) if sort_field else None
        else:
            item_id = getattr(last_item, id_field, None)
            created_at = getattr(last_item, created_at_field, None) if created_at_field else None
            sort_value = getattr(last_item, sort_field, None) if sort_field else None

        if item_id is not None:
            next_cursor = encode_cursor(
                id=item_id,
                created_at=created_at,
                field=sort_field,
                value=sort_value,
            )

    return PaginatedResponse(
        items=page_items,
        next_cursor=next_cursor,
        has_more=has_more,
    )

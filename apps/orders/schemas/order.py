"""Order request/response schemas.

Defines Pydantic schemas for order management endpoints.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SortDirection(str, Enum):
    """Sort direction enumeration."""

    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """Sort parameters for order listing."""

    field: str = Field(
        default="created_at",
        description="Field to sort by",
        json_schema_extra={"example": "created_at"},
    )
    direction: SortDirection = Field(
        default=SortDirection.DESC,
        description="Sort direction",
        json_schema_extra={"example": "desc"},
    )


class OrderFilters(BaseModel):
    """Filter parameters for order listing."""

    status: str | None = Field(
        default=None,
        description="Filter by order status",
        json_schema_extra={"example": "pending"},
    )
    customer_id: UUID | None = Field(
        default=None,
        description="Filter by customer ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    date_from: datetime | None = Field(
        default=None,
        description="Filter orders created after this date",
        json_schema_extra={"example": "2024-01-01T00:00:00Z"},
    )
    date_to: datetime | None = Field(
        default=None,
        description="Filter orders created before this date",
        json_schema_extra={"example": "2024-12-31T23:59:59Z"},
    )


class AddressSchema(BaseModel):
    """Address schema for shipping and billing."""

    street: str = Field(
        ...,
        max_length=255,
        description="Street address",
        json_schema_extra={"example": "123 Main St"},
    )
    city: str = Field(
        ...,
        max_length=100,
        description="City",
        json_schema_extra={"example": "New York"},
    )
    state: str = Field(
        ...,
        max_length=100,
        description="State or province",
        json_schema_extra={"example": "NY"},
    )
    postal_code: str = Field(
        ...,
        max_length=20,
        description="Postal code",
        json_schema_extra={"example": "10001"},
    )
    country: str = Field(
        ...,
        max_length=100,
        description="Country",
        json_schema_extra={"example": "USA"},
    )


class CreateOrderItemRequest(BaseModel):
    """Order item creation request schema."""

    product_id: str = Field(
        ...,
        max_length=255,
        description="Product identifier",
        json_schema_extra={"example": "PROD-001"},
    )
    product_name: str = Field(
        ...,
        max_length=255,
        description="Product name",
        json_schema_extra={"example": "Wireless Headphones"},
    )
    quantity: int = Field(
        ...,
        ge=1,
        description="Quantity ordered",
        json_schema_extra={"example": 2},
    )
    unit_price: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Price per unit",
        json_schema_extra={"example": "49.99"},
    )


class CreateOrderRequest(BaseModel):
    """Order creation request schema."""

    items: list[CreateOrderItemRequest] = Field(
        ...,
        min_length=1,
        description="List of order items",
    )
    currency: str = Field(
        default="USD",
        max_length=3,
        description="Currency code",
        json_schema_extra={"example": "USD"},
    )
    shipping_address: AddressSchema = Field(
        ...,
        description="Shipping address",
    )
    billing_address: AddressSchema | None = Field(
        default=None,
        description="Billing address (defaults to shipping address if not provided)",
    )


class UpdateOrderRequest(BaseModel):
    """Order update request schema."""

    status: str | None = Field(
        default=None,
        description="New order status",
        json_schema_extra={"example": "confirmed"},
    )
    shipping_address: AddressSchema | None = Field(
        default=None,
        description="Updated shipping address",
    )
    billing_address: AddressSchema | None = Field(
        default=None,
        description="Updated billing address",
    )


class OrderItemResponse(BaseModel):
    """Order item response schema."""

    model_config = {"from_attributes": True}

    id: UUID = Field(
        ...,
        description="Order item ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440001"},
    )
    product_id: str = Field(
        ...,
        description="Product identifier",
        json_schema_extra={"example": "PROD-001"},
    )
    product_name: str = Field(
        ...,
        description="Product name",
        json_schema_extra={"example": "Wireless Headphones"},
    )
    quantity: int = Field(
        ...,
        description="Quantity ordered",
        json_schema_extra={"example": 2},
    )
    unit_price: Decimal = Field(
        ...,
        description="Price per unit",
        json_schema_extra={"example": "49.99"},
    )
    total_price: Decimal = Field(
        ...,
        description="Total price for this item",
        json_schema_extra={"example": "99.98"},
    )


class OrderResponse(BaseModel):
    """Order response schema."""

    model_config = {"from_attributes": True}

    id: UUID = Field(
        ...,
        description="Order ID",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440000"},
    )
    user_id: UUID = Field(
        ...,
        description="User ID who placed the order",
        json_schema_extra={"example": "550e8400-e29b-41d4-a716-446655440002"},
    )
    status: str = Field(
        ...,
        description="Order status",
        json_schema_extra={"example": "pending"},
    )
    total_amount: Decimal = Field(
        ...,
        description="Total order amount",
        json_schema_extra={"example": "199.98"},
    )
    currency: str = Field(
        ...,
        description="Currency code",
        json_schema_extra={"example": "USD"},
    )
    shipping_address: dict[str, Any] = Field(
        ...,
        description="Shipping address",
    )
    billing_address: dict[str, Any] = Field(
        ...,
        description="Billing address",
    )
    items: list[OrderItemResponse] = Field(
        default_factory=list,
        description="Order items",
    )
    created_at: datetime = Field(
        ...,
        description="Order creation timestamp",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"},
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )

"""Order and OrderItem SQLModels for e-commerce.

Defines the Order and OrderItem database models.
"""

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(SQLModel, table=True):
    """Order database model."""

    __tablename__ = "orders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    total_amount: Decimal = Field(decimal_places=2, max_digits=12)
    currency: str = Field(default="USD", max_length=3)
    shipping_address: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    billing_address: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None)

    # Relationships
    items: list["OrderItem"] = Relationship(back_populates="order")

    model_config = ConfigDict(from_attributes=True)


class OrderItem(SQLModel, table=True):
    """Order item database model."""

    __tablename__ = "order_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    order_id: UUID = Field(foreign_key="orders.id", index=True)
    product_id: str = Field(max_length=255)
    product_name: str = Field(max_length=255)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(decimal_places=2, max_digits=12)
    total_price: Decimal = Field(decimal_places=2, max_digits=12)

    # Relationships
    order: Order = Relationship(back_populates="items")

    model_config = ConfigDict(from_attributes=True)

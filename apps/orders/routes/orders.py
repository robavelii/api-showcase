"""Orders API routes.

Provides endpoints for order management.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from apps.orders.schemas.order import (
    CreateOrderRequest,
    OrderFilters,
    OrderResponse,
    SortDirection,
    SortParams,
    UpdateOrderRequest,
)
from apps.orders.services.order_service import OrderService, get_order_service
from shared.pagination.cursor import PaginatedResponse

router = APIRouter()


@router.get(
    "/orders",
    response_model=PaginatedResponse[OrderResponse],
    summary="List orders",
    description="Get a paginated list of orders with optional filtering and sorting.",
    responses={
        200: {
            "description": "List of orders",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440000",
                                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                                "status": "pending",
                                "total_amount": "99.99",
                                "currency": "USD",
                                "shipping_address": {"street": "123 Main St"},
                                "billing_address": {"street": "123 Main St"},
                                "items": [],
                                "created_at": "2024-01-15T10:30:00Z",
                                "updated_at": None,
                            }
                        ],
                        "next_cursor": None,
                        "has_more": False,
                    }
                }
            },
        }
    },
)
async def list_orders(
    cursor: Annotated[str | None, Query(description="Pagination cursor")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page size")] = 20,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    customer_id: Annotated[UUID | None, Query(description="Filter by customer")] = None,
    sort_field: Annotated[str, Query(description="Sort field")] = "created_at",
    sort_direction: Annotated[
        SortDirection, Query(description="Sort direction")
    ] = SortDirection.DESC,
    order_service: OrderService = Depends(get_order_service),
) -> PaginatedResponse[OrderResponse]:
    """List orders with pagination, filtering, and sorting."""
    filters = OrderFilters(status=status, customer_id=customer_id)
    sort = SortParams(field=sort_field, direction=sort_direction)

    return order_service.list_orders(
        cursor=cursor,
        limit=limit,
        filters=filters,
        sort=sort,
    )


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create order",
    description="Create a new order with items.",
    responses={
        201: {
            "description": "Order created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "user_id": "550e8400-e29b-41d4-a716-446655440001",
                        "status": "pending",
                        "total_amount": "99.99",
                        "currency": "USD",
                        "shipping_address": {
                            "street": "123 Main St",
                            "city": "New York",
                            "state": "NY",
                            "postal_code": "10001",
                            "country": "USA",
                        },
                        "billing_address": {
                            "street": "123 Main St",
                            "city": "New York",
                            "state": "NY",
                            "postal_code": "10001",
                            "country": "USA",
                        },
                        "items": [
                            {
                                "id": "550e8400-e29b-41d4-a716-446655440002",
                                "product_id": "PROD-001",
                                "product_name": "Wireless Headphones",
                                "quantity": 2,
                                "unit_price": "49.99",
                                "total_price": "99.98",
                            }
                        ],
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": None,
                    }
                }
            },
        }
    },
)
async def create_order(
    data: CreateOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Create a new order."""
    # In a real app, user_id would come from authentication
    # For demo, we use a placeholder UUID
    from uuid import uuid4

    user_id = uuid4()

    return order_service.create_order(data, user_id)


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order",
    description="Get order details by ID.",
    responses={
        200: {
            "description": "Order details",
        },
        404: {
            "description": "Order not found",
        },
    },
)
async def get_order(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Get an order by ID."""
    order = order_service.get_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order


@router.patch(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Update order",
    description="Update an existing order.",
    responses={
        200: {
            "description": "Order updated successfully",
        },
        404: {
            "description": "Order not found",
        },
    },
)
async def update_order(
    order_id: UUID,
    data: UpdateOrderRequest,
    order_service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Update an existing order."""
    order = order_service.update_order(order_id, data)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order

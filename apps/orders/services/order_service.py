"""Order service for CRUD operations.

Provides business logic for order management.
"""

from datetime import datetime, UTC
from decimal import Decimal
from typing import Any
from uuid import UUID

from apps.orders.models.order import Order, OrderItem, OrderStatus
from apps.orders.schemas.order import (
    CreateOrderRequest,
    OrderFilters,
    OrderResponse,
    SortDirection,
    SortParams,
    UpdateOrderRequest,
)
from shared.pagination.cursor import (
    PaginatedResponse,
    decode_cursor,
    encode_cursor,
)


class OrderService:
    """Service for order management operations."""

    def __init__(self):
        """Initialize order service with in-memory storage for demo."""
        self._orders: dict[UUID, Order] = {}
        self._order_items: dict[UUID, list[OrderItem]] = {}

    def list_orders(
        self,
        cursor: str | None = None,
        limit: int = 20,
        filters: OrderFilters | None = None,
        sort: SortParams | None = None,
        user_id: UUID | None = None,
    ) -> PaginatedResponse[OrderResponse]:
        """List orders with cursor pagination, filtering, and sorting.

        Args:
            cursor: Pagination cursor from previous response
            limit: Maximum number of items to return
            filters: Filter criteria
            sort: Sort parameters
            user_id: Optional user ID to filter by owner

        Returns:
            Paginated list of orders
        """
        if sort is None:
            sort = SortParams()
        if filters is None:
            filters = OrderFilters()

        # Get all orders
        orders = list(self._orders.values())

        # Apply user filter if provided
        if user_id is not None:
            orders = [o for o in orders if o.user_id == user_id]

        # Apply filters
        orders = self._apply_filters(orders, filters)

        # Apply sorting
        orders = self._apply_sorting(orders, sort)


        # Apply cursor-based pagination
        if cursor:
            cursor_data = decode_cursor(cursor)
            cursor_id = UUID(cursor_data.id)
            # Find the index of the cursor item and start after it
            cursor_idx = None
            for idx, order in enumerate(orders):
                if order.id == cursor_id:
                    cursor_idx = idx
                    break
            if cursor_idx is not None:
                orders = orders[cursor_idx + 1:]

        # Get one extra to determine if there are more
        page_orders = orders[:limit + 1]
        has_more = len(page_orders) > limit
        page_orders = page_orders[:limit]

        # Build next cursor
        next_cursor = None
        if has_more and page_orders:
            last_order = page_orders[-1]
            next_cursor = encode_cursor(
                id=last_order.id,
                created_at=last_order.created_at,
                field=sort.field,
                value=getattr(last_order, sort.field, None),
            )

        # Convert to response models
        items = [self._to_response(o) for o in page_orders]

        return PaginatedResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _apply_filters(
        self, orders: list[Order], filters: OrderFilters
    ) -> list[Order]:
        """Apply filter criteria to orders list."""
        result = orders

        if filters.status:
            result = [o for o in result if o.status.value == filters.status]

        if filters.customer_id:
            result = [o for o in result if o.user_id == filters.customer_id]

        if filters.date_from:
            result = [o for o in result if o.created_at >= filters.date_from]

        if filters.date_to:
            result = [o for o in result if o.created_at <= filters.date_to]

        return result

    def _apply_sorting(
        self, orders: list[Order], sort: SortParams
    ) -> list[Order]:
        """Apply sorting to orders list."""
        reverse = sort.direction == SortDirection.DESC

        def get_sort_key(order: Order) -> Any:
            value = getattr(order, sort.field, None)
            if value is None:
                # Handle None values - put them at the end
                return (1, "")
            return (0, value)

        return sorted(orders, key=get_sort_key, reverse=reverse)

    def create_order(
        self, data: CreateOrderRequest, user_id: UUID
    ) -> OrderResponse:
        """Create a new order.

        Args:
            data: Order creation data
            user_id: ID of the user creating the order

        Returns:
            Created order response
        """
        # Calculate total amount
        total_amount = Decimal("0")
        order_items: list[OrderItem] = []

        for item_data in data.items:
            item_total = item_data.unit_price * item_data.quantity
            total_amount += item_total

            order_item = OrderItem(
                product_id=item_data.product_id,
                product_name=item_data.product_name,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=item_total,
            )
            order_items.append(order_item)

        # Create order
        billing_addr = data.billing_address or data.shipping_address
        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            currency=data.currency,
            shipping_address=data.shipping_address.model_dump(),
            billing_address=billing_addr.model_dump(),
        )

        # Link items to order
        for item in order_items:
            item.order_id = order.id

        # Store in memory
        self._orders[order.id] = order
        self._order_items[order.id] = order_items

        return self._to_response(order)

    def get_order(self, order_id: UUID) -> OrderResponse | None:
        """Get an order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order response or None if not found
        """
        order = self._orders.get(order_id)
        if order is None:
            return None
        return self._to_response(order)

    def update_order(
        self, order_id: UUID, data: UpdateOrderRequest
    ) -> OrderResponse | None:
        """Update an existing order.

        Args:
            order_id: Order ID
            data: Update data

        Returns:
            Updated order response or None if not found
        """
        order = self._orders.get(order_id)
        if order is None:
            return None

        # Update fields
        if data.status is not None:
            try:
                order.status = OrderStatus(data.status)
            except ValueError:
                pass  # Invalid status, ignore

        if data.shipping_address is not None:
            order.shipping_address = data.shipping_address.model_dump()

        if data.billing_address is not None:
            order.billing_address = data.billing_address.model_dump()

        order.updated_at = datetime.now(UTC)

        return self._to_response(order)

    def _to_response(self, order: Order) -> OrderResponse:
        """Convert Order model to response schema."""
        items = self._order_items.get(order.id, [])
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            status=order.status.value,
            total_amount=order.total_amount,
            currency=order.currency,
            shipping_address=order.shipping_address,
            billing_address=order.billing_address,
            items=items,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )


# Global service instance for dependency injection
_order_service: OrderService | None = None


def get_order_service() -> OrderService:
    """Get or create the order service instance."""
    global _order_service
    if _order_service is None:
        _order_service = OrderService()
    return _order_service

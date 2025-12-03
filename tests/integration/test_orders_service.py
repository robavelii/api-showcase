"""Integration tests for the Orders service.

Tests order CRUD operations, filtering, sorting, and pagination.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from apps.orders.models.order import Order, OrderStatus
from apps.orders.schemas.order import (
    AddressSchema,
    CreateOrderItemRequest,
    CreateOrderRequest,
    OrderFilters,
    SortDirection,
    SortParams,
    UpdateOrderRequest,
)
from apps.orders.services.order_service import OrderService


class TestOrderServiceCreation:
    """Tests for order creation."""

    @pytest.fixture
    def service(self):
        """Create a fresh OrderService instance."""
        return OrderService()

    @pytest.fixture
    def valid_address(self):
        """Create a valid address schema."""
        return AddressSchema(
            street="123 Test Street",
            city="Test City",
            state="TS",
            postal_code="12345",
            country="USA",
        )

    @pytest.fixture
    def valid_item(self):
        """Create a valid order item request."""
        return CreateOrderItemRequest(
            product_id="PROD-001",
            product_name="Test Product",
            quantity=2,
            unit_price=Decimal("25.00"),
        )

    def test_create_order_success(self, service, valid_address, valid_item):
        """Test successful order creation."""
        request = CreateOrderRequest(
            items=[valid_item],
            currency="USD",
            shipping_address=valid_address,
        )
        user_id = uuid4()

        result = service.create_order(request, user_id)

        assert result.id is not None
        assert result.user_id == user_id
        assert result.status == "pending"
        assert result.currency == "USD"
        assert result.total_amount == Decimal("50.00")  # 2 * 25.00

    def test_create_order_calculates_total_correctly(self, service, valid_address):
        """Test order total calculation with multiple items."""
        items = [
            CreateOrderItemRequest(
                product_id="PROD-001",
                product_name="Product 1",
                quantity=3,
                unit_price=Decimal("10.00"),
            ),
            CreateOrderItemRequest(
                product_id="PROD-002",
                product_name="Product 2",
                quantity=2,
                unit_price=Decimal("15.50"),
            ),
        ]
        request = CreateOrderRequest(
            items=items,
            currency="USD",
            shipping_address=valid_address,
        )

        result = service.create_order(request, uuid4())

        expected_total = Decimal("30.00") + Decimal("31.00")  # 3*10 + 2*15.50
        assert result.total_amount == expected_total

    def test_create_order_uses_billing_address_if_provided(self, service, valid_address):
        """Test that billing address is used when provided."""
        billing_address = AddressSchema(
            street="456 Billing St",
            city="Billing City",
            state="BC",
            postal_code="67890",
            country="USA",
        )
        item = CreateOrderItemRequest(
            product_id="PROD-001",
            product_name="Test",
            quantity=1,
            unit_price=Decimal("10.00"),
        )
        request = CreateOrderRequest(
            items=[item],
            currency="USD",
            shipping_address=valid_address,
            billing_address=billing_address,
        )

        result = service.create_order(request, uuid4())

        assert result.billing_address["street"] == "456 Billing St"
        assert result.shipping_address["street"] == "123 Test Street"

    def test_create_multiple_orders_have_unique_ids(self, service, valid_address, valid_item):
        """Test that multiple orders have unique IDs."""
        request = CreateOrderRequest(
            items=[valid_item],
            currency="USD",
            shipping_address=valid_address,
        )

        ids = set()
        for _ in range(10):
            result = service.create_order(request, uuid4())
            ids.add(result.id)

        assert len(ids) == 10


class TestOrderServiceRetrieval:
    """Tests for order retrieval."""

    @pytest.fixture
    def service_with_orders(self):
        """Create a service with pre-populated orders."""
        service = OrderService()
        user_id = uuid4()

        for i in range(5):
            order = Order(
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_amount=Decimal(str(100 + i * 10)),
                currency="USD",
                shipping_address={"street": f"Street {i}"},
                billing_address={"street": f"Street {i}"},
            )
            service._orders[order.id] = order
            service._order_items[order.id] = []

        return service, user_id

    def test_get_order_by_id(self, service_with_orders):
        """Test retrieving an order by ID."""
        service, _ = service_with_orders
        order_id = list(service._orders.keys())[0]

        result = service.get_order(order_id)

        assert result is not None
        assert result.id == order_id

    def test_get_nonexistent_order_returns_none(self, service_with_orders):
        """Test retrieving non-existent order returns None."""
        service, _ = service_with_orders

        result = service.get_order(uuid4())

        assert result is None

    def test_list_orders_returns_all_orders(self, service_with_orders):
        """Test listing all orders."""
        service, _ = service_with_orders

        result = service.list_orders(limit=100)

        assert len(result.items) == 5


class TestOrderServiceFiltering:
    """Tests for order filtering."""

    @pytest.fixture
    def service_with_varied_orders(self):
        """Create a service with orders of various statuses and users."""
        service = OrderService()
        user1 = uuid4()
        user2 = uuid4()

        statuses = [
            OrderStatus.PENDING,
            OrderStatus.CONFIRMED,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]

        for i, status in enumerate(statuses):
            order = Order(
                user_id=user1 if i % 2 == 0 else user2,
                status=status,
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "Test"},
                billing_address={"street": "Test"},
            )
            service._orders[order.id] = order
            service._order_items[order.id] = []

        return service, user1, user2

    def test_filter_by_status(self, service_with_varied_orders):
        """Test filtering orders by status."""
        service, _, _ = service_with_varied_orders

        filters = OrderFilters(status="pending")
        result = service.list_orders(filters=filters, limit=100)

        assert all(order.status == "pending" for order in result.items)

    def test_filter_by_customer_id(self, service_with_varied_orders):
        """Test filtering orders by customer ID."""
        service, user1, _ = service_with_varied_orders

        filters = OrderFilters(customer_id=user1)
        result = service.list_orders(filters=filters, limit=100)

        assert all(order.user_id == user1 for order in result.items)

    def test_filter_by_date_range(self):
        """Test filtering orders by date range."""
        service = OrderService()
        base_date = datetime(2024, 6, 15)

        for i in range(10):
            order = Order(
                user_id=uuid4(),
                status=OrderStatus.PENDING,
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "Test"},
                billing_address={"street": "Test"},
            )
            order.created_at = base_date + timedelta(days=i - 5)
            service._orders[order.id] = order
            service._order_items[order.id] = []

        date_from = base_date - timedelta(days=2)
        date_to = base_date + timedelta(days=2)
        filters = OrderFilters(date_from=date_from, date_to=date_to)
        result = service.list_orders(filters=filters, limit=100)

        for order in result.items:
            assert order.created_at >= date_from
            assert order.created_at <= date_to


class TestOrderServiceSorting:
    """Tests for order sorting."""

    @pytest.fixture
    def service_with_orders(self):
        """Create a service with orders of varying amounts and dates."""
        service = OrderService()
        base_date = datetime(2024, 1, 1)

        for i in range(5):
            order = Order(
                user_id=uuid4(),
                status=OrderStatus.PENDING,
                total_amount=Decimal(str(100 + i * 50)),
                currency="USD",
                shipping_address={"street": "Test"},
                billing_address={"street": "Test"},
            )
            order.created_at = base_date + timedelta(days=i)
            service._orders[order.id] = order
            service._order_items[order.id] = []

        return service

    def test_sort_by_created_at_ascending(self, service_with_orders):
        """Test sorting by created_at ascending."""
        sort = SortParams(field="created_at", direction=SortDirection.ASC)
        result = service_with_orders.list_orders(sort=sort, limit=100)

        for i in range(len(result.items) - 1):
            assert result.items[i].created_at <= result.items[i + 1].created_at

    def test_sort_by_created_at_descending(self, service_with_orders):
        """Test sorting by created_at descending."""
        sort = SortParams(field="created_at", direction=SortDirection.DESC)
        result = service_with_orders.list_orders(sort=sort, limit=100)

        for i in range(len(result.items) - 1):
            assert result.items[i].created_at >= result.items[i + 1].created_at

    def test_sort_by_total_amount_ascending(self, service_with_orders):
        """Test sorting by total_amount ascending."""
        sort = SortParams(field="total_amount", direction=SortDirection.ASC)
        result = service_with_orders.list_orders(sort=sort, limit=100)

        for i in range(len(result.items) - 1):
            assert result.items[i].total_amount <= result.items[i + 1].total_amount

    def test_sort_by_total_amount_descending(self, service_with_orders):
        """Test sorting by total_amount descending."""
        sort = SortParams(field="total_amount", direction=SortDirection.DESC)
        result = service_with_orders.list_orders(sort=sort, limit=100)

        for i in range(len(result.items) - 1):
            assert result.items[i].total_amount >= result.items[i + 1].total_amount


class TestOrderServicePagination:
    """Tests for order pagination."""

    @pytest.fixture
    def service_with_many_orders(self):
        """Create a service with many orders for pagination testing."""
        service = OrderService()
        base_date = datetime(2024, 1, 1)

        for i in range(25):
            order = Order(
                user_id=uuid4(),
                status=OrderStatus.PENDING,
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "Test"},
                billing_address={"street": "Test"},
            )
            order.created_at = base_date + timedelta(seconds=i)
            service._orders[order.id] = order
            service._order_items[order.id] = []

        return service

    def test_pagination_limits_results(self, service_with_many_orders):
        """Test that pagination limits the number of results."""
        result = service_with_many_orders.list_orders(limit=10)

        assert len(result.items) == 10
        assert result.has_more is True
        assert result.next_cursor is not None

    def test_pagination_cursor_continues_from_last(self, service_with_many_orders):
        """Test that cursor pagination continues from the last item."""
        first_page = service_with_many_orders.list_orders(limit=10)
        second_page = service_with_many_orders.list_orders(cursor=first_page.next_cursor, limit=10)

        first_ids = {order.id for order in first_page.items}
        second_ids = {order.id for order in second_page.items}

        assert len(first_ids & second_ids) == 0  # No overlap

    def test_pagination_last_page_has_no_more(self, service_with_many_orders):
        """Test that the last page indicates no more items."""
        result = service_with_many_orders.list_orders(limit=100)

        assert result.has_more is False
        assert result.next_cursor is None


class TestOrderServiceUpdate:
    """Tests for order updates."""

    @pytest.fixture
    def service_with_order(self):
        """Create a service with a single order."""
        service = OrderService()
        address = AddressSchema(
            street="123 Test St",
            city="Test City",
            state="TS",
            postal_code="12345",
            country="USA",
        )
        item = CreateOrderItemRequest(
            product_id="PROD-001",
            product_name="Test",
            quantity=1,
            unit_price=Decimal("10.00"),
        )
        request = CreateOrderRequest(
            items=[item],
            currency="USD",
            shipping_address=address,
        )
        order = service.create_order(request, uuid4())
        return service, order.id

    def test_update_order_status(self, service_with_order):
        """Test updating order status."""
        service, order_id = service_with_order

        update = UpdateOrderRequest(status="confirmed")
        result = service.update_order(order_id, update)

        assert result.status == "confirmed"

    def test_update_order_shipping_address(self, service_with_order):
        """Test updating shipping address."""
        service, order_id = service_with_order

        new_address = AddressSchema(
            street="456 New St",
            city="New City",
            state="NC",
            postal_code="67890",
            country="USA",
        )
        update = UpdateOrderRequest(shipping_address=new_address)
        result = service.update_order(order_id, update)

        assert result.shipping_address["street"] == "456 New St"

    def test_update_sets_updated_at(self, service_with_order):
        """Test that update sets the updated_at timestamp."""
        service, order_id = service_with_order

        # Initially updated_at should be None
        original = service.get_order(order_id)
        assert original.updated_at is None

        update = UpdateOrderRequest(status="confirmed")
        result = service.update_order(order_id, update)

        assert result.updated_at is not None

    def test_update_nonexistent_order_returns_none(self, service_with_order):
        """Test updating non-existent order returns None."""
        service, _ = service_with_order

        update = UpdateOrderRequest(status="confirmed")
        result = service.update_order(uuid4(), update)

        assert result is None

"""Property-based tests for Orders API.

**Feature: openapi-showcase**
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from hypothesis import assume, given, settings
from hypothesis import strategies as st

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

# Strategies for generating test data
uuid_strategy = st.uuids()
datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
)
status_strategy = st.sampled_from([s.value for s in OrderStatus])
decimal_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("9999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)
positive_int_strategy = st.integers(min_value=1, max_value=100)


def create_address_schema():
    """Create a valid address schema for testing."""
    return AddressSchema(
        street="123 Test St",
        city="Test City",
        state="TS",
        postal_code="12345",
        country="USA",
    )


def create_order_item_request(
    product_id: str = "PROD-001",
    product_name: str = "Test Product",
    quantity: int = 1,
    unit_price: Decimal = Decimal("10.00"),
) -> CreateOrderItemRequest:
    """Create a valid order item request for testing."""
    return CreateOrderItemRequest(
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
    )


class TestOrderFilteringProperties:
    """
    **Feature: openapi-showcase, Property 8: Filter correctness**
    """

    @settings(max_examples=100)
    @given(
        num_orders=st.integers(min_value=1, max_value=20),
        filter_status=status_strategy,
    )
    def test_status_filter_returns_only_matching_orders(self, num_orders: int, filter_status: str):
        """
        **Feature: openapi-showcase, Property 8: Filter correctness**

        For any filter criteria (status), all orders returned by list_orders
        SHALL match the specified filter condition.
        """
        service = OrderService()

        # Create orders with various statuses
        statuses = list(OrderStatus)
        for i in range(num_orders):
            order = Order(
                user_id=uuid4(),
                status=statuses[i % len(statuses)],
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "123 Test St"},
                billing_address={"street": "123 Test St"},
            )
            service._orders[order.id] = order
            service._order_items[order.id] = []

        # Apply status filter
        filters = OrderFilters(status=filter_status)
        result = service.list_orders(filters=filters, limit=100)

        # Verify all returned orders match the filter
        for order in result.items:
            assert order.status == filter_status

    @settings(max_examples=100)
    @given(
        num_orders=st.integers(min_value=1, max_value=20),
    )
    def test_customer_id_filter_returns_only_matching_orders(self, num_orders: int):
        """
        **Feature: openapi-showcase, Property 8: Filter correctness**

        For any customer_id filter, all orders returned SHALL belong to
        that customer.
        """
        service = OrderService()
        target_user_id = uuid4()

        # Create orders for different users
        for i in range(num_orders):
            user_id = target_user_id if i % 3 == 0 else uuid4()
            order = Order(
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "123 Test St"},
                billing_address={"street": "123 Test St"},
            )
            service._orders[order.id] = order
            service._order_items[order.id] = []

        # Apply customer_id filter
        filters = OrderFilters(customer_id=target_user_id)
        result = service.list_orders(filters=filters, limit=100)

        # Verify all returned orders belong to the target user
        for order in result.items:
            assert order.user_id == target_user_id

    @settings(max_examples=50)
    @given(
        num_orders=st.integers(min_value=5, max_value=20),
    )
    def test_date_range_filter_returns_orders_in_range(self, num_orders: int):
        """
        **Feature: openapi-showcase, Property 8: Filter correctness**

        For any date range filter, all orders returned SHALL have
        created_at within the specified range.
        """
        service = OrderService()
        base_date = datetime(2024, 6, 15)

        # Create orders with different dates
        for i in range(num_orders):
            order = Order(
                user_id=uuid4(),
                status=OrderStatus.PENDING,
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "123 Test St"},
                billing_address={"street": "123 Test St"},
            )
            # Spread orders across a month
            order.created_at = base_date + timedelta(days=i - num_orders // 2)
            service._orders[order.id] = order
            service._order_items[order.id] = []

        # Apply date range filter
        date_from = base_date - timedelta(days=5)
        date_to = base_date + timedelta(days=5)
        filters = OrderFilters(date_from=date_from, date_to=date_to)
        result = service.list_orders(filters=filters, limit=100)

        # Verify all returned orders are within the date range
        for order in result.items:
            assert order.created_at >= date_from
            assert order.created_at <= date_to


class TestOrderSortingProperties:
    """
    **Feature: openapi-showcase, Property 9: Sort correctness**
    """

    @settings(max_examples=100)
    @given(
        num_orders=st.integers(min_value=2, max_value=20),
        direction=st.sampled_from([SortDirection.ASC, SortDirection.DESC]),
    )
    def test_sort_by_created_at_returns_correct_order(
        self, num_orders: int, direction: SortDirection
    ):
        """
        **Feature: openapi-showcase, Property 9: Sort correctness**

        For any sort parameter (field + direction), the orders returned
        SHALL be in the correct sorted order.
        """
        service = OrderService()
        base_date = datetime(2024, 1, 1)

        # Create orders with different timestamps
        for i in range(num_orders):
            order = Order(
                user_id=uuid4(),
                status=OrderStatus.PENDING,
                total_amount=Decimal("100.00"),
                currency="USD",
                shipping_address={"street": "123 Test St"},
                billing_address={"street": "123 Test St"},
            )
            order.created_at = base_date + timedelta(days=i)
            service._orders[order.id] = order
            service._order_items[order.id] = []

        # Apply sorting
        sort = SortParams(field="created_at", direction=direction)
        result = service.list_orders(sort=sort, limit=100)

        # Verify order is correct
        if len(result.items) >= 2:
            for i in range(len(result.items) - 1):
                if direction == SortDirection.ASC:
                    assert result.items[i].created_at <= result.items[i + 1].created_at
                else:
                    assert result.items[i].created_at >= result.items[i + 1].created_at

    @settings(max_examples=100)
    @given(
        num_orders=st.integers(min_value=2, max_value=20),
        direction=st.sampled_from([SortDirection.ASC, SortDirection.DESC]),
    )
    def test_sort_by_total_amount_returns_correct_order(
        self, num_orders: int, direction: SortDirection
    ):
        """
        **Feature: openapi-showcase, Property 9: Sort correctness**

        For any sort by total_amount, orders SHALL be in correct order.
        """
        service = OrderService()

        # Create orders with different amounts
        for i in range(num_orders):
            order = Order(
                user_id=uuid4(),
                status=OrderStatus.PENDING,
                total_amount=Decimal(str(100 + i * 10)),
                currency="USD",
                shipping_address={"street": "123 Test St"},
                billing_address={"street": "123 Test St"},
            )
            service._orders[order.id] = order
            service._order_items[order.id] = []

        # Apply sorting
        sort = SortParams(field="total_amount", direction=direction)
        result = service.list_orders(sort=sort, limit=100)

        # Verify order is correct
        if len(result.items) >= 2:
            for i in range(len(result.items) - 1):
                if direction == SortDirection.ASC:
                    assert result.items[i].total_amount <= result.items[i + 1].total_amount
                else:
                    assert result.items[i].total_amount >= result.items[i + 1].total_amount


class TestOrderCreationProperties:
    """
    **Feature: openapi-showcase, Property 10: Order creation idempotency check**
    """

    @settings(max_examples=100)
    @given(
        num_orders=st.integers(min_value=2, max_value=50),
    )
    def test_order_creation_produces_unique_ids(self, num_orders: int):
        """
        **Feature: openapi-showcase, Property 10: Order creation idempotency check**

        For any valid order creation request, POST /orders SHALL create
        an order with a unique UUID that does not collide with any existing order ID.
        """
        service = OrderService()
        created_ids = set()

        for _ in range(num_orders):
            request = CreateOrderRequest(
                items=[create_order_item_request()],
                currency="USD",
                shipping_address=create_address_schema(),
            )
            user_id = uuid4()

            order = service.create_order(request, user_id)

            # Verify ID is unique
            assert order.id not in created_ids
            created_ids.add(order.id)

        # Verify all IDs are unique
        assert len(created_ids) == num_orders

    @settings(max_examples=100)
    @given(
        quantity=st.integers(min_value=1, max_value=100),
        unit_price=decimal_strategy,
    )
    def test_order_total_calculated_correctly(self, quantity: int, unit_price: Decimal):
        """
        **Feature: openapi-showcase, Property 10: Order creation idempotency check**

        For any order creation, the total_amount SHALL equal the sum of
        all item totals (quantity * unit_price).
        """
        service = OrderService()

        item = CreateOrderItemRequest(
            product_id="PROD-001",
            product_name="Test Product",
            quantity=quantity,
            unit_price=unit_price,
        )

        request = CreateOrderRequest(
            items=[item],
            currency="USD",
            shipping_address=create_address_schema(),
        )

        order = service.create_order(request, uuid4())

        expected_total = unit_price * quantity
        assert order.total_amount == expected_total


class TestOrderRetrievalProperties:
    """
    **Feature: openapi-showcase, Property 11: Order retrieval consistency**
    """

    @settings(max_examples=100)
    @given(
        quantity=st.integers(min_value=1, max_value=10),
        unit_price=decimal_strategy,
    )
    def test_created_order_can_be_retrieved(self, quantity: int, unit_price: Decimal):
        """
        **Feature: openapi-showcase, Property 11: Order retrieval consistency**

        For any created order, GET /orders/{id} SHALL return order data
        that matches the data used to create it.
        """
        service = OrderService()

        item = CreateOrderItemRequest(
            product_id="PROD-001",
            product_name="Test Product",
            quantity=quantity,
            unit_price=unit_price,
        )

        request = CreateOrderRequest(
            items=[item],
            currency="USD",
            shipping_address=create_address_schema(),
        )

        user_id = uuid4()
        created_order = service.create_order(request, user_id)

        # Retrieve the order
        retrieved_order = service.get_order(created_order.id)

        # Verify consistency
        assert retrieved_order is not None
        assert retrieved_order.id == created_order.id
        assert retrieved_order.user_id == user_id
        assert retrieved_order.total_amount == created_order.total_amount
        assert retrieved_order.currency == "USD"
        assert retrieved_order.status == "pending"

    @settings(max_examples=50)
    @given(
        num_items=st.integers(min_value=1, max_value=5),
    )
    def test_order_items_preserved_on_retrieval(self, num_items: int):
        """
        **Feature: openapi-showcase, Property 11: Order retrieval consistency**

        For any created order with items, retrieval SHALL return all items
        with correct data.
        """
        service = OrderService()

        items = [
            CreateOrderItemRequest(
                product_id=f"PROD-{i:03d}",
                product_name=f"Product {i}",
                quantity=i + 1,
                unit_price=Decimal(str(10 * (i + 1))),
            )
            for i in range(num_items)
        ]

        request = CreateOrderRequest(
            items=items,
            currency="USD",
            shipping_address=create_address_schema(),
        )

        created_order = service.create_order(request, uuid4())
        retrieved_order = service.get_order(created_order.id)

        # Verify items count
        assert len(retrieved_order.items) == num_items

        # Verify item data
        for i, item in enumerate(retrieved_order.items):
            assert item.product_id == f"PROD-{i:03d}"
            assert item.quantity == i + 1


class TestOrderUpdateProperties:
    """
    **Feature: openapi-showcase, Property 12: Order update persistence**
    """

    @settings(max_examples=100)
    @given(
        new_status=status_strategy,
    )
    def test_order_status_update_persists(self, new_status: str):
        """
        **Feature: openapi-showcase, Property 12: Order update persistence**

        For any valid order update, PATCH /orders/{id} followed by
        GET /orders/{id} SHALL return the updated values.
        """
        service = OrderService()

        # Create an order
        request = CreateOrderRequest(
            items=[create_order_item_request()],
            currency="USD",
            shipping_address=create_address_schema(),
        )
        created_order = service.create_order(request, uuid4())

        # Update the order
        update_request = UpdateOrderRequest(status=new_status)
        updated_order = service.update_order(created_order.id, update_request)

        # Retrieve and verify
        retrieved_order = service.get_order(created_order.id)

        assert updated_order.status == new_status
        assert retrieved_order.status == new_status

    @settings(max_examples=50)
    @given(
        new_street=st.text(
            min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789 "
        ),
    )
    def test_order_address_update_persists(self, new_street: str):
        """
        **Feature: openapi-showcase, Property 12: Order update persistence**

        For any address update, the new address SHALL be persisted.
        """
        service = OrderService()

        # Create an order
        request = CreateOrderRequest(
            items=[create_order_item_request()],
            currency="USD",
            shipping_address=create_address_schema(),
        )
        created_order = service.create_order(request, uuid4())

        # Update shipping address
        new_address = AddressSchema(
            street=new_street,
            city="New City",
            state="NC",
            postal_code="99999",
            country="USA",
        )
        update_request = UpdateOrderRequest(shipping_address=new_address)
        service.update_order(created_order.id, update_request)

        # Retrieve and verify
        retrieved_order = service.get_order(created_order.id)

        assert retrieved_order.shipping_address["street"] == new_street
        assert retrieved_order.shipping_address["city"] == "New City"

    @settings(max_examples=50)
    @given(
        new_status=status_strategy,
    )
    def test_order_updated_at_changes_on_update(self, new_status: str):
        """
        **Feature: openapi-showcase, Property 12: Order update persistence**

        For any update, the updated_at timestamp SHALL be set.
        """
        service = OrderService()

        # Create an order
        request = CreateOrderRequest(
            items=[create_order_item_request()],
            currency="USD",
            shipping_address=create_address_schema(),
        )
        created_order = service.create_order(request, uuid4())

        # Initially updated_at should be None
        assert created_order.updated_at is None

        # Update the order
        update_request = UpdateOrderRequest(status=new_status)
        updated_order = service.update_order(created_order.id, update_request)

        # updated_at should now be set
        assert updated_order.updated_at is not None


class TestWebhookSignatureProperties:
    """
    **Feature: openapi-showcase, Property 13: Webhook signature verification**
    """

    @settings(max_examples=100)
    @given(
        payload_content=st.text(
            min_size=1, max_size=500, alphabet='abcdefghijklmnopqrstuvwxyz0123456789{}":, '
        ),
    )
    def test_valid_signature_is_accepted(self, payload_content: str):
        """
        **Feature: openapi-showcase, Property 13: Webhook signature verification**

        For any webhook payload, a valid HMAC-SHA256 signature SHALL be accepted.
        """
        import hashlib
        import hmac
        import time

        from apps.orders.services.webhook_service import WebhookService

        service = WebhookService()
        secret = "whsec_test_secret"

        # Create payload
        payload = payload_content.encode("utf-8")
        timestamp = str(int(time.time()))

        # Compute valid signature
        signed_payload = f"{timestamp}.{payload_content}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Create Stripe-style signature header
        sig_header = f"t={timestamp},v1={signature}"

        # Verify signature is accepted
        result = service.verify_stripe_signature(payload, sig_header, secret)
        assert result is True

    @settings(max_examples=100)
    @given(
        payload_content=st.text(
            min_size=1, max_size=200, alphabet='abcdefghijklmnopqrstuvwxyz0123456789{}":, '
        ),
        tampered_content=st.text(
            min_size=1, max_size=200, alphabet='abcdefghijklmnopqrstuvwxyz0123456789{}":, '
        ),
    )
    def test_modified_payload_is_rejected(self, payload_content: str, tampered_content: str):
        """
        **Feature: openapi-showcase, Property 13: Webhook signature verification**

        For any modified payload, the signature verification SHALL fail.
        """
        assume(payload_content != tampered_content)

        import hashlib
        import hmac
        import time

        from apps.orders.services.webhook_service import WebhookService

        service = WebhookService()
        secret = "whsec_test_secret"

        # Create signature for original payload
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{payload_content}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={timestamp},v1={signature}"

        # Try to verify with tampered payload
        tampered_payload = tampered_content.encode("utf-8")
        result = service.verify_stripe_signature(tampered_payload, sig_header, secret)

        assert result is False

    @settings(max_examples=100)
    @given(
        payload_content=st.text(
            min_size=1, max_size=200, alphabet='abcdefghijklmnopqrstuvwxyz0123456789{}":, '
        ),
        wrong_secret=st.text(
            min_size=10, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"
        ),
    )
    def test_wrong_secret_is_rejected(self, payload_content: str, wrong_secret: str):
        """
        **Feature: openapi-showcase, Property 13: Webhook signature verification**

        For any signature created with a different secret, verification SHALL fail.
        """
        assume(wrong_secret != "whsec_test_secret")

        import hashlib
        import hmac
        import time

        from apps.orders.services.webhook_service import WebhookService

        service = WebhookService()
        correct_secret = "whsec_test_secret"

        # Create signature with wrong secret
        payload = payload_content.encode("utf-8")
        timestamp = str(int(time.time()))
        signed_payload = f"{timestamp}.{payload_content}"
        signature = hmac.new(
            wrong_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={timestamp},v1={signature}"

        # Verify with correct secret should fail
        result = service.verify_stripe_signature(payload, sig_header, correct_secret)

        assert result is False

    @settings(max_examples=50)
    @given(
        payload_content=st.text(
            min_size=1, max_size=200, alphabet='abcdefghijklmnopqrstuvwxyz0123456789{}":, '
        ),
    )
    def test_expired_timestamp_is_rejected(self, payload_content: str):
        """
        **Feature: openapi-showcase, Property 13: Webhook signature verification**

        For any signature with an expired timestamp (>5 minutes old),
        verification SHALL fail.
        """
        import hashlib
        import hmac
        import time

        from apps.orders.services.webhook_service import WebhookService

        service = WebhookService()
        secret = "whsec_test_secret"

        # Create signature with old timestamp (10 minutes ago)
        payload = payload_content.encode("utf-8")
        old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
        signed_payload = f"{old_timestamp}.{payload_content}"
        signature = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        sig_header = f"t={old_timestamp},v1={signature}"

        # Verify should fail due to expired timestamp
        result = service.verify_stripe_signature(payload, sig_header, secret)

        assert result is False

    def test_invalid_signature_format_is_rejected(self):
        """
        **Feature: openapi-showcase, Property 13: Webhook signature verification**

        Invalid signature formats SHALL be rejected.
        """
        from apps.orders.services.webhook_service import WebhookService

        service = WebhookService()
        payload = b'{"test": "data"}'

        # Test various invalid formats
        invalid_signatures = [
            "",
            "invalid",
            "t=123",
            "v1=abc",
            "t=abc,v1=def",  # non-numeric timestamp
        ]

        for sig in invalid_signatures:
            result = service.verify_stripe_signature(payload, sig, "secret")
            assert result is False

"""Integration tests for the Webhook Tester service.

Tests bin management and event capture functionality.
"""

from uuid import uuid4

import pytest

from apps.webhook_tester.schemas.bin import CreateBinRequest
from apps.webhook_tester.services.bin_service import BinService
from apps.webhook_tester.services.event_service import EventService, MockRequest
from shared.pagination.cursor import PaginationParams


class TestBinServiceCreation:
    """Tests for webhook bin creation."""

    @pytest.fixture
    def service(self):
        """Create a fresh BinService instance."""
        return BinService(base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_create_bin_success(self, service):
        """Test successful bin creation."""
        user_id = uuid4()
        request = CreateBinRequest(name="Test Bin")

        result = await service.create_bin(user_id, request)

        assert result.id is not None
        assert result.user_id == user_id
        assert result.name == "Test Bin"
        assert result.is_active is True
        assert "https://api.test.com" in result.url

    @pytest.mark.asyncio
    async def test_create_bin_without_name(self, service):
        """Test bin creation without a name."""
        user_id = uuid4()

        result = await service.create_bin(user_id, None)

        assert result.id is not None
        assert result.name == ""

    @pytest.mark.asyncio
    async def test_create_multiple_bins_unique_ids(self, service):
        """Test that multiple bins have unique IDs."""
        user_id = uuid4()
        ids = set()

        for _ in range(10):
            result = await service.create_bin(user_id, None)
            ids.add(result.id)

        assert len(ids) == 10


class TestBinServiceRetrieval:
    """Tests for webhook bin retrieval."""

    @pytest.fixture
    def service(self):
        """Create a fresh BinService instance."""
        return BinService(base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_get_bin_by_id(self, service):
        """Test retrieving a bin by ID."""
        user_id = uuid4()
        created = await service.create_bin(user_id, CreateBinRequest(name="Test"))

        result = await service.get_bin(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_bin_returns_none(self, service):
        """Test retrieving non-existent bin returns None."""
        result = await service.get_bin(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_list_bins_returns_only_user_bins(self, service):
        """Test listing bins returns only bins owned by the user."""
        user1 = uuid4()
        user2 = uuid4()

        # Create bins for both users
        for _ in range(3):
            await service.create_bin(user1, None)
        for _ in range(2):
            await service.create_bin(user2, None)

        result1 = await service.list_bins(user1)
        result2 = await service.list_bins(user2)

        assert len(result1) == 3
        assert len(result2) == 2
        assert all(b.user_id == user1 for b in result1)
        assert all(b.user_id == user2 for b in result2)

    @pytest.mark.asyncio
    async def test_list_bins_sorted_by_created_at_descending(self, service):
        """Test that bins are sorted by created_at descending."""
        user_id = uuid4()

        for i in range(5):
            await service.create_bin(user_id, CreateBinRequest(name=f"Bin {i}"))

        result = await service.list_bins(user_id)

        for i in range(len(result) - 1):
            assert result[i].created_at >= result[i + 1].created_at


class TestBinServiceDeletion:
    """Tests for webhook bin deletion."""

    @pytest.fixture
    def service(self):
        """Create a fresh BinService instance."""
        return BinService(base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_delete_bin_success(self, service):
        """Test successful bin deletion."""
        user_id = uuid4()
        created = await service.create_bin(user_id, None)

        result = await service.delete_bin(created.id, user_id)

        assert result is True
        assert await service.get_bin(created.id) is None

    @pytest.mark.asyncio
    async def test_delete_bin_wrong_user_fails(self, service):
        """Test that deleting another user's bin fails."""
        user1 = uuid4()
        user2 = uuid4()
        created = await service.create_bin(user1, None)

        result = await service.delete_bin(created.id, user2)

        assert result is False
        assert await service.get_bin(created.id) is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_bin_returns_false(self, service):
        """Test deleting non-existent bin returns False."""
        result = await service.delete_bin(uuid4(), uuid4())

        assert result is False


class TestBinServiceDeactivation:
    """Tests for webhook bin deactivation."""

    @pytest.fixture
    def service(self):
        """Create a fresh BinService instance."""
        return BinService(base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_deactivate_bin_success(self, service):
        """Test successful bin deactivation."""
        user_id = uuid4()
        created = await service.create_bin(user_id, None)

        result = await service.deactivate_bin(created.id, user_id)

        assert result is not None
        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_bin_wrong_user_fails(self, service):
        """Test that deactivating another user's bin fails."""
        user1 = uuid4()
        user2 = uuid4()
        created = await service.create_bin(user1, None)

        result = await service.deactivate_bin(created.id, user2)

        assert result is None


class TestBinServiceCounting:
    """Tests for bin counting functionality."""

    @pytest.fixture
    def service(self):
        """Create a fresh BinService instance."""
        return BinService(base_url="https://api.test.com")

    @pytest.mark.asyncio
    async def test_get_bin_count(self, service):
        """Test getting bin count for a user."""
        user_id = uuid4()

        for _ in range(5):
            await service.create_bin(user_id, None)

        count = service.get_bin_count(user_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_bin_count_empty(self, service):
        """Test getting bin count for user with no bins."""
        count = service.get_bin_count(uuid4())

        assert count == 0


class TestEventServiceCapture:
    """Tests for webhook event capture."""

    @pytest.fixture
    def service(self):
        """Create a fresh EventService instance."""
        return EventService()

    @pytest.mark.asyncio
    async def test_capture_event_success(self, service):
        """Test successful event capture."""
        bin_id = uuid4()
        request = MockRequest(
            method="POST",
            path="/webhook",
            headers={"Content-Type": "application/json"},
            body='{"test": "data"}',
            source_ip="192.168.1.1",
        )

        result = await service.capture_event(bin_id, request)

        assert result.id is not None
        assert result.bin_id == bin_id
        assert result.method == "POST"
        assert result.path == "/webhook"
        assert result.body == '{"test": "data"}'
        assert result.source_ip == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_capture_event_preserves_headers(self, service):
        """Test that event capture preserves all headers."""
        bin_id = uuid4()
        headers = {
            "Content-Type": "application/json",
            "X-Custom-Header": "custom-value",
            "Authorization": "Bearer token123",
        }
        request = MockRequest(method="POST", path="/", headers=headers, body="")

        result = await service.capture_event(bin_id, request)

        assert result.headers["Content-Type"] == "application/json"
        assert result.headers["X-Custom-Header"] == "custom-value"
        assert result.headers["Authorization"] == "Bearer token123"

    @pytest.mark.asyncio
    async def test_capture_event_preserves_query_params(self, service):
        """Test that event capture preserves query parameters."""
        bin_id = uuid4()
        request = MockRequest(
            method="GET",
            path="/webhook",
            query_params={"key": "value", "foo": "bar"},
        )

        result = await service.capture_event(bin_id, request)

        assert result.query_params["key"] == "value"
        assert result.query_params["foo"] == "bar"


class TestEventServiceRetrieval:
    """Tests for webhook event retrieval."""

    @pytest.fixture
    def service(self):
        """Create a fresh EventService instance."""
        return EventService()

    @pytest.mark.asyncio
    async def test_list_events_returns_bin_events(self, service):
        """Test listing events for a specific bin."""
        bin_id = uuid4()

        for i in range(5):
            request = MockRequest(method="POST", path=f"/webhook/{i}", body="")
            await service.capture_event(bin_id, request)

        result = await service.list_events(bin_id)

        assert len(result.items) == 5

    @pytest.mark.asyncio
    async def test_list_events_isolated_by_bin(self, service):
        """Test that events are isolated by bin."""
        bin1 = uuid4()
        bin2 = uuid4()

        for _ in range(3):
            await service.capture_event(bin1, MockRequest(method="POST", path="/", body=""))
        for _ in range(2):
            await service.capture_event(bin2, MockRequest(method="POST", path="/", body=""))

        result1 = await service.list_events(bin1)
        result2 = await service.list_events(bin2)

        assert len(result1.items) == 3
        assert len(result2.items) == 2

    @pytest.mark.asyncio
    async def test_list_events_reverse_chronological_order(self, service):
        """Test that events are returned in reverse chronological order."""
        bin_id = uuid4()

        for i in range(5):
            request = MockRequest(method="POST", path=f"/webhook/{i}", body="")
            await service.capture_event(bin_id, request)

        result = await service.list_events(bin_id)

        for i in range(len(result.items) - 1):
            assert result.items[i].received_at >= result.items[i + 1].received_at

    @pytest.mark.asyncio
    async def test_get_event_by_id(self, service):
        """Test retrieving a specific event by ID."""
        bin_id = uuid4()
        request = MockRequest(method="POST", path="/test", body="test body")
        captured = await service.capture_event(bin_id, request)

        result = await service.get_event(bin_id, captured.id)

        assert result is not None
        assert result.id == captured.id
        assert result.path == "/test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_event_returns_none(self, service):
        """Test retrieving non-existent event returns None."""
        result = await service.get_event(uuid4(), uuid4())

        assert result is None


class TestEventServicePagination:
    """Tests for event pagination."""

    @pytest.fixture
    def service(self):
        """Create a fresh EventService instance."""
        return EventService()

    @pytest.mark.asyncio
    async def test_pagination_limits_results(self, service):
        """Test that pagination limits results."""
        bin_id = uuid4()

        for _ in range(25):
            await service.capture_event(bin_id, MockRequest(method="POST", path="/", body=""))

        pagination = PaginationParams(limit=10)
        result = await service.list_events(bin_id, pagination)

        assert len(result.items) == 10
        assert result.has_more is True
        assert result.next_cursor is not None

    @pytest.mark.asyncio
    async def test_pagination_cursor_continues(self, service):
        """Test that cursor pagination continues correctly."""
        bin_id = uuid4()

        for _ in range(25):
            await service.capture_event(bin_id, MockRequest(method="POST", path="/", body=""))

        first_page = await service.list_events(bin_id, PaginationParams(limit=10))
        second_page = await service.list_events(
            bin_id, PaginationParams(limit=10, cursor=first_page.next_cursor)
        )

        first_ids = {e.id for e in first_page.items}
        second_ids = {e.id for e in second_page.items}

        assert len(first_ids & second_ids) == 0  # No overlap


class TestEventServiceCounting:
    """Tests for event counting and clearing."""

    @pytest.fixture
    def service(self):
        """Create a fresh EventService instance."""
        return EventService()

    @pytest.mark.asyncio
    async def test_get_event_count(self, service):
        """Test getting event count for a bin."""
        bin_id = uuid4()

        for _ in range(5):
            await service.capture_event(bin_id, MockRequest(method="POST", path="/", body=""))

        count = service.get_event_count(bin_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_clear_events(self, service):
        """Test clearing all events for a bin."""
        bin_id = uuid4()

        for _ in range(5):
            await service.capture_event(bin_id, MockRequest(method="POST", path="/", body=""))

        cleared = service.clear_events(bin_id)
        count = service.get_event_count(bin_id)

        assert cleared == 5
        assert count == 0

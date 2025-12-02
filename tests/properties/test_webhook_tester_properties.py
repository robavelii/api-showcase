"""Property-based tests for webhook tester API.

**Feature: openapi-showcase**
"""

from datetime import datetime, UTC
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings, strategies as st

from apps.webhook_tester.models.bin import WebhookBin
from apps.webhook_tester.models.event import BinEvent
from apps.webhook_tester.schemas.bin import BinResponse, CreateBinRequest
from apps.webhook_tester.schemas.event import EventResponse
from apps.webhook_tester.services.bin_service import BinService


# Strategies for generating test data
uuid_strategy = st.uuids()
name_strategy = st.text(min_size=0, max_size=100)
method_strategy = st.sampled_from(["GET", "POST", "PUT", "PATCH", "DELETE"])
path_strategy = st.text(min_size=1, max_size=200).map(lambda x: "/" + x.lstrip("/"))
ip_strategy = st.ip_addresses().map(str)
content_type_strategy = st.sampled_from([
    "application/json",
    "application/xml",
    "text/plain",
    "application/x-www-form-urlencoded",
])
body_strategy = st.text(min_size=0, max_size=1000)
headers_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50).filter(
        lambda x: x.strip() and x.isascii() and x.lower() != "content-type"
    ),
    values=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    min_size=0,
    max_size=10,
)
query_params_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=30).filter(lambda x: x.strip() and x.isascii()),
    values=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    min_size=0,
    max_size=5,
)


class TestBinCreationUniquenessProperties:
    """
    **Feature: openapi-showcase, Property 24: Bin creation uniqueness**
    """

    @settings(max_examples=100)
    @given(
        user_id=uuid_strategy,
        name=name_strategy,
    )
    @pytest.mark.asyncio
    async def test_bin_creation_produces_unique_id(
        self, user_id: UUID, name: str
    ):
        """
        **Feature: openapi-showcase, Property 24: Bin creation uniqueness**
        
        For any bin creation request, POST /bins SHALL create a bin with a unique ID
        that does not collide with existing bins.
        """
        service = BinService()
        request = CreateBinRequest(name=name)
        
        # Create the bin
        bin_response = await service.create_bin(user_id, request)
        
        # Bin should have a valid UUID
        assert bin_response.id is not None
        assert isinstance(bin_response.id, UUID)
        
        # Bin should have correct user_id
        assert bin_response.user_id == user_id
        
        # Bin should have the provided name
        assert bin_response.name == name
        
        # Bin should be active by default
        assert bin_response.is_active is True
        
        # Bin should have a URL
        assert str(bin_response.id) in bin_response.url

    @settings(max_examples=100)
    @given(
        user_id=uuid_strategy,
        num_bins=st.integers(min_value=2, max_value=10),
    )
    @pytest.mark.asyncio
    async def test_multiple_bins_have_unique_ids(
        self, user_id: UUID, num_bins: int
    ):
        """
        **Feature: openapi-showcase, Property 24: Bin creation uniqueness**
        
        For any number of bin creation requests, all created bins SHALL have
        unique IDs that do not collide with each other.
        """
        service = BinService()
        created_ids = set()
        
        for i in range(num_bins):
            request = CreateBinRequest(name=f"Bin {i}")
            bin_response = await service.create_bin(user_id, request)
            
            # ID should not already exist
            assert bin_response.id not in created_ids, f"Duplicate ID found: {bin_response.id}"
            
            created_ids.add(bin_response.id)
        
        # All IDs should be unique
        assert len(created_ids) == num_bins


class TestBinOwnershipIsolationProperties:
    """
    **Feature: openapi-showcase, Property 26: Bin ownership isolation**
    """

    @settings(max_examples=100)
    @given(
        user1_id=uuid_strategy,
        user2_id=uuid_strategy,
        user1_bins=st.integers(min_value=1, max_value=5),
        user2_bins=st.integers(min_value=1, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_list_bins_returns_only_owned_bins(
        self,
        user1_id: UUID,
        user2_id: UUID,
        user1_bins: int,
        user2_bins: int,
    ):
        """
        **Feature: openapi-showcase, Property 26: Bin ownership isolation**
        
        For any user, GET /bins SHALL return only bins owned by that user
        and no bins owned by other users.
        """
        # Ensure different users
        if user1_id == user2_id:
            user2_id = uuid4()
        
        service = BinService()
        
        # Create bins for user1
        user1_created_ids = set()
        for i in range(user1_bins):
            bin_response = await service.create_bin(user1_id, CreateBinRequest(name=f"User1 Bin {i}"))
            user1_created_ids.add(bin_response.id)
        
        # Create bins for user2
        user2_created_ids = set()
        for i in range(user2_bins):
            bin_response = await service.create_bin(user2_id, CreateBinRequest(name=f"User2 Bin {i}"))
            user2_created_ids.add(bin_response.id)
        
        # List bins for user1
        user1_list = await service.list_bins(user1_id)
        user1_list_ids = {b.id for b in user1_list}
        
        # User1 should see only their bins
        assert user1_list_ids == user1_created_ids
        
        # User1 should not see user2's bins
        assert user1_list_ids.isdisjoint(user2_created_ids)
        
        # List bins for user2
        user2_list = await service.list_bins(user2_id)
        user2_list_ids = {b.id for b in user2_list}
        
        # User2 should see only their bins
        assert user2_list_ids == user2_created_ids
        
        # User2 should not see user1's bins
        assert user2_list_ids.isdisjoint(user1_created_ids)

    @settings(max_examples=100)
    @given(
        owner_id=uuid_strategy,
        other_user_id=uuid_strategy,
    )
    @pytest.mark.asyncio
    async def test_delete_bin_requires_ownership(
        self,
        owner_id: UUID,
        other_user_id: UUID,
    ):
        """
        **Feature: openapi-showcase, Property 26: Bin ownership isolation**
        
        For any bin, only the owner SHALL be able to delete it.
        """
        # Ensure different users
        if owner_id == other_user_id:
            other_user_id = uuid4()
        
        service = BinService()
        
        # Create a bin for owner
        bin_response = await service.create_bin(owner_id, CreateBinRequest(name="Test Bin"))
        bin_id = bin_response.id
        
        # Other user should not be able to delete
        result = await service.delete_bin(bin_id, other_user_id)
        assert result is False
        
        # Bin should still exist
        bin_check = await service.get_bin(bin_id)
        assert bin_check is not None
        
        # Owner should be able to delete
        result = await service.delete_bin(bin_id, owner_id)
        assert result is True
        
        # Bin should no longer exist
        bin_check = await service.get_bin(bin_id)
        assert bin_check is None



class TestRequestCaptureCompletenessProperties:
    """
    **Feature: openapi-showcase, Property 25: Request capture completeness**
    """

    @settings(max_examples=100)
    @given(
        bin_id=uuid_strategy,
        method=method_strategy,
        path=path_strategy,
        headers=headers_strategy,
        body=body_strategy,
        content_type=content_type_strategy,
        source_ip=ip_strategy,
        query_params=query_params_strategy,
    )
    @pytest.mark.asyncio
    async def test_captured_event_contains_all_request_details(
        self,
        bin_id: UUID,
        method: str,
        path: str,
        headers: dict,
        body: str,
        content_type: str,
        source_ip: str,
        query_params: dict,
    ):
        """
        **Feature: openapi-showcase, Property 25: Request capture completeness**
        
        For any HTTP request sent to POST /{bin_id}, the captured event SHALL
        contain the original method, headers, body, content-type, and source IP.
        """
        from apps.webhook_tester.services.event_service import EventService, MockRequest
        
        service = EventService()
        
        # Add content-type to headers
        full_headers = {**headers, "Content-Type": content_type}
        
        # Create mock request
        mock_request = MockRequest(
            method=method,
            path=path,
            headers=full_headers,
            body=body,
            content_type=content_type,
            source_ip=source_ip,
            query_params=query_params,
        )
        
        # Capture the event
        event = await service.capture_event(bin_id, mock_request)
        
        # Verify all request details are captured
        assert event.method == method
        assert event.path == path
        assert event.body == body
        assert event.content_type == content_type
        assert event.source_ip == source_ip
        
        # Verify headers are captured (case-insensitive comparison)
        for key, value in full_headers.items():
            assert key in event.headers or key.lower() in {k.lower() for k in event.headers}
        
        # Verify query params are captured
        assert event.query_params == query_params
        
        # Verify event has valid ID and timestamp
        assert event.id is not None
        assert event.bin_id == bin_id
        assert event.received_at is not None

    @settings(max_examples=100)
    @given(
        bin_id=uuid_strategy,
        num_events=st.integers(min_value=1, max_value=10),
    )
    @pytest.mark.asyncio
    async def test_multiple_events_captured_independently(
        self,
        bin_id: UUID,
        num_events: int,
    ):
        """
        **Feature: openapi-showcase, Property 25: Request capture completeness**
        
        For any number of requests to a bin, each event SHALL be captured
        independently with unique IDs.
        """
        from apps.webhook_tester.services.event_service import EventService, MockRequest
        
        service = EventService()
        captured_ids = set()
        
        for i in range(num_events):
            mock_request = MockRequest(
                method="POST",
                path=f"/webhook/{i}",
                headers={"X-Event-Number": str(i)},
                body=f'{{"event": {i}}}',
            )
            
            event = await service.capture_event(bin_id, mock_request)
            
            # Each event should have a unique ID
            assert event.id not in captured_ids
            captured_ids.add(event.id)
        
        # All events should be stored
        assert service.get_event_count(bin_id) == num_events
        assert len(captured_ids) == num_events



class TestEventRetrievalProperties:
    """
    **Feature: openapi-showcase, Property 27: Event retrieval for bin**
    """

    @settings(max_examples=100)
    @given(
        bin_id=uuid_strategy,
        num_events=st.integers(min_value=1, max_value=20),
    )
    @pytest.mark.asyncio
    async def test_events_returned_in_reverse_chronological_order(
        self,
        bin_id: UUID,
        num_events: int,
    ):
        """
        **Feature: openapi-showcase, Property 27: Event retrieval for bin**
        
        For any bin with captured events, GET /{bin_id}/events SHALL return
        all events for that bin in reverse chronological order.
        """
        from apps.webhook_tester.services.event_service import EventService, MockRequest
        
        service = EventService()
        
        # Capture multiple events
        for i in range(num_events):
            mock_request = MockRequest(
                method="POST",
                path=f"/webhook/{i}",
                body=f'{{"event": {i}}}',
            )
            await service.capture_event(bin_id, mock_request)
        
        # List events
        result = await service.list_events(bin_id)
        
        # All events should be returned
        assert len(result.items) == num_events
        
        # Events should be in reverse chronological order
        for i in range(len(result.items) - 1):
            assert result.items[i].received_at >= result.items[i + 1].received_at

    @settings(max_examples=100)
    @given(
        bin1_id=uuid_strategy,
        bin2_id=uuid_strategy,
    )
    @pytest.mark.asyncio
    async def test_events_isolated_by_bin(
        self,
        bin1_id: UUID,
        bin2_id: UUID,
    ):
        """
        **Feature: openapi-showcase, Property 27: Event retrieval for bin**
        
        For any two bins, events captured in one bin SHALL NOT appear
        in the other bin's event list.
        """
        # Ensure different bins
        if bin1_id == bin2_id:
            bin2_id = uuid4()
        
        from apps.webhook_tester.services.event_service import EventService, MockRequest
        
        service = EventService()
        
        # Capture events in bin1
        bin1_event_ids = set()
        for i in range(3):
            mock_request = MockRequest(method="POST", body=f'{{"bin1_event": {i}}}')
            event = await service.capture_event(bin1_id, mock_request)
            bin1_event_ids.add(event.id)
        
        # Capture events in bin2
        bin2_event_ids = set()
        for i in range(3):
            mock_request = MockRequest(method="POST", body=f'{{"bin2_event": {i}}}')
            event = await service.capture_event(bin2_id, mock_request)
            bin2_event_ids.add(event.id)
        
        # List events for bin1
        bin1_result = await service.list_events(bin1_id)
        bin1_result_ids = {e.id for e in bin1_result.items}
        
        # Bin1 should only have its own events
        assert bin1_result_ids == bin1_event_ids
        assert bin1_result_ids.isdisjoint(bin2_event_ids)
        
        # List events for bin2
        bin2_result = await service.list_events(bin2_id)
        bin2_result_ids = {e.id for e in bin2_result.items}
        
        # Bin2 should only have its own events
        assert bin2_result_ids == bin2_event_ids
        assert bin2_result_ids.isdisjoint(bin1_event_ids)


class TestWebhookEventRoundTripProperties:
    """
    **Feature: openapi-showcase, Property 28: Webhook event round-trip**
    """

    @settings(max_examples=100)
    @given(
        bin_id=uuid_strategy,
        method=method_strategy,
        path=path_strategy,
        headers=headers_strategy,
        body=body_strategy,
        content_type=content_type_strategy,
        source_ip=ip_strategy,
        query_params=query_params_strategy,
    )
    def test_event_response_json_round_trip(
        self,
        bin_id: UUID,
        method: str,
        path: str,
        headers: dict,
        body: str,
        content_type: str,
        source_ip: str,
        query_params: dict,
    ):
        """
        **Feature: openapi-showcase, Property 28: Webhook event round-trip**
        
        For any valid WebhookEvent object, serializing to JSON and deserializing
        back SHALL produce an equivalent WebhookEvent object.
        """
        event_id = uuid4()
        received_at = datetime.now(UTC)
        
        # Create event response
        event = EventResponse(
            id=event_id,
            bin_id=bin_id,
            method=method,
            path=path,
            headers=headers,
            body=body,
            content_type=content_type,
            source_ip=source_ip,
            query_params=query_params,
            received_at=received_at,
        )
        
        # Serialize to JSON
        json_str = event.model_dump_json()
        
        # Deserialize back
        restored = EventResponse.model_validate_json(json_str)
        
        # Verify round-trip consistency
        assert restored.id == event.id
        assert restored.bin_id == event.bin_id
        assert restored.method == event.method
        assert restored.path == event.path
        assert restored.headers == event.headers
        assert restored.body == event.body
        assert restored.content_type == event.content_type
        assert restored.source_ip == event.source_ip
        assert restored.query_params == event.query_params
        # Note: datetime comparison may have microsecond precision differences
        assert abs((restored.received_at - event.received_at).total_seconds()) < 1

    @settings(max_examples=100)
    @given(
        bin_id=uuid_strategy,
        name=name_strategy,
    )
    def test_bin_response_json_round_trip(
        self,
        bin_id: UUID,
        name: str,
    ):
        """
        **Feature: openapi-showcase, Property 28: Webhook event round-trip**
        
        For any valid BinResponse object, serializing to JSON and deserializing
        back SHALL produce an equivalent BinResponse object.
        """
        user_id = uuid4()
        created_at = datetime.now(UTC)
        
        # Create bin response
        bin_response = BinResponse(
            id=bin_id,
            user_id=user_id,
            name=name,
            is_active=True,
            created_at=created_at,
            url=f"https://api.example.com/{bin_id}",
        )
        
        # Serialize to JSON
        json_str = bin_response.model_dump_json()
        
        # Deserialize back
        restored = BinResponse.model_validate_json(json_str)
        
        # Verify round-trip consistency
        assert restored.id == bin_response.id
        assert restored.user_id == bin_response.user_id
        assert restored.name == bin_response.name
        assert restored.is_active == bin_response.is_active
        assert restored.url == bin_response.url
        # Note: datetime comparison may have microsecond precision differences
        assert abs((restored.created_at - bin_response.created_at).total_seconds()) < 1

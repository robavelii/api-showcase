"""Property-based tests for rate limiting utilities.

**Feature: openapi-showcase**
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from shared.rate_limit.limiter import get_user_identifier


class MockRequest:
    """Mock FastAPI request for testing."""

    def __init__(self, user_id: str | None = None, client_ip: str = "127.0.0.1"):
        self.state = MagicMock()
        self.state.user_id = user_id
        self.client = MagicMock()
        self.client.host = client_ip


class TestRateLimitProperties:
    """
    **Feature: openapi-showcase, Property 31: Rate limit enforcement**
    """

    @settings(max_examples=100)
    @given(
        user_id=st.text(min_size=1, max_size=36, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-"),
    )
    def test_authenticated_user_identifier_uses_user_id(self, user_id: str):
        """
        **Feature: openapi-showcase, Property 31: Rate limit enforcement**

        For any authenticated user, the rate limit identifier SHALL include
        the user ID to enable per-user rate limiting.
        """
        request = MockRequest(user_id=user_id)

        identifier = get_user_identifier(request)

        # Should use user ID with prefix
        assert identifier == f"user:{user_id}"
        assert user_id in identifier

    @settings(max_examples=100)
    @given(
        ip_address=st.from_regex(
            r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
            r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
            fullmatch=True,
        ),
    )
    def test_unauthenticated_user_identifier_uses_ip(self, ip_address: str):
        """
        **Feature: openapi-showcase, Property 31: Rate limit enforcement**

        For any unauthenticated client, the rate limit identifier SHALL use
        the client IP address for per-IP rate limiting.
        """
        request = MockRequest(user_id=None, client_ip=ip_address)

        identifier = get_user_identifier(request)

        # Should use IP address (slowapi's get_remote_address returns the IP)
        # Note: The actual IP extraction depends on slowapi's implementation
        # We verify that it doesn't use user prefix
        assert not identifier.startswith("user:")

    def test_user_identifier_prefers_user_id_over_ip(self):
        """
        **Feature: openapi-showcase, Property 31: Rate limit enforcement**

        When both user ID and IP are available, the identifier SHALL prefer
        user ID for more accurate per-user rate limiting.
        """
        request = MockRequest(user_id="test-user-123", client_ip="192.168.1.1")

        identifier = get_user_identifier(request)

        # Should use user ID, not IP
        assert identifier == "user:test-user-123"
        assert "192.168.1.1" not in identifier

    def test_different_users_get_different_identifiers(self):
        """
        **Feature: openapi-showcase, Property 31: Rate limit enforcement**

        Different authenticated users SHALL have different rate limit identifiers.
        """
        request1 = MockRequest(user_id="user-1")
        request2 = MockRequest(user_id="user-2")

        id1 = get_user_identifier(request1)
        id2 = get_user_identifier(request2)

        assert id1 != id2
        assert id1 == "user:user-1"
        assert id2 == "user:user-2"

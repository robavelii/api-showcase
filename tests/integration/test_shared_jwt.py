"""Integration tests for JWT utilities.

Tests token creation, validation, and blocklist functionality.
"""

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest

from shared.auth.jwt import (
    TokenBlocklist,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    get_token_jti,
)


class TestAccessTokenCreation:
    """Tests for access token creation."""

    def test_create_access_token_success(self):
        """Test successful access token creation."""
        user_id = uuid4()

        token = create_access_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_user_id(self):
        """Test that access token contains user ID."""
        user_id = uuid4()

        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload.sub == str(user_id)

    def test_create_access_token_has_correct_type(self):
        """Test that access token has correct type claim."""
        token = create_access_token(uuid4())
        payload = decode_token(token)

        assert payload.type == "access"

    def test_create_access_token_with_custom_expiry(self):
        """Test access token with custom expiry."""
        user_id = uuid4()
        expires_delta = timedelta(hours=1)

        token = create_access_token(user_id, expires_delta=expires_delta)
        payload = decode_token(token)

        # Token should be valid (not expired)
        assert payload.sub == str(user_id)

    def test_create_access_token_with_additional_claims(self):
        """Test access token with additional claims."""
        user_id = uuid4()
        additional_claims = {"role": "admin", "permissions": ["read", "write"]}

        token = create_access_token(user_id, additional_claims=additional_claims)

        # Decode without validation to check claims
        from shared.config import get_settings

        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestRefreshTokenCreation:
    """Tests for refresh token creation."""

    def test_create_refresh_token_success(self):
        """Test successful refresh token creation."""
        user_id = uuid4()

        token = create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)

    def test_create_refresh_token_has_correct_type(self):
        """Test that refresh token has correct type claim."""
        token = create_refresh_token(uuid4())
        payload = decode_token(token)

        assert payload.type == "refresh"

    def test_create_refresh_token_with_custom_expiry(self):
        """Test refresh token with custom expiry."""
        user_id = uuid4()
        expires_delta = timedelta(days=30)

        token = create_refresh_token(user_id, expires_delta=expires_delta)
        payload = decode_token(token)

        assert payload.sub == str(user_id)


class TestTokenPairCreation:
    """Tests for token pair creation."""

    def test_create_token_pair_success(self):
        """Test successful token pair creation."""
        user_id = uuid4()

        pair = create_token_pair(user_id)

        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.token_type == "bearer"

    def test_token_pair_tokens_are_different(self):
        """Test that access and refresh tokens are different."""
        pair = create_token_pair(uuid4())

        assert pair.access_token != pair.refresh_token

    def test_token_pair_tokens_have_correct_types(self):
        """Test that tokens in pair have correct types."""
        pair = create_token_pair(uuid4())

        access_payload = decode_token(pair.access_token)
        refresh_payload = decode_token(pair.refresh_token)

        assert access_payload.type == "access"
        assert refresh_payload.type == "refresh"


class TestTokenDecoding:
    """Tests for token decoding."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        user_id = uuid4()
        token = create_access_token(user_id)

        payload = decode_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == str(user_id)
        assert payload.type == "access"
        assert payload.jti is not None

    def test_decode_expired_token_raises_error(self):
        """Test that decoding expired token raises error."""
        user_id = uuid4()
        token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_decode_expired_token_without_verification(self):
        """Test decoding expired token without expiry verification."""
        user_id = uuid4()
        token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

        payload = decode_token(token, verify_exp=False)

        assert payload.sub == str(user_id)

    def test_decode_invalid_token_raises_error(self):
        """Test that decoding invalid token raises error."""
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("invalid.token.here")

    def test_decode_tampered_token_raises_error(self):
        """Test that decoding tampered token raises error."""
        token = create_access_token(uuid4())
        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "xxxxx"
        tampered_token = ".".join(parts)

        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered_token)


class TestTokenJtiExtraction:
    """Tests for JTI extraction."""

    def test_get_token_jti_success(self):
        """Test extracting JTI from token."""
        token = create_access_token(uuid4())

        jti = get_token_jti(token)

        assert jti is not None
        assert isinstance(jti, str)
        assert len(jti) > 0

    def test_get_token_jti_from_expired_token(self):
        """Test extracting JTI from expired token."""
        token = create_access_token(uuid4(), expires_delta=timedelta(seconds=-1))

        jti = get_token_jti(token)

        assert jti is not None

    def test_jti_is_unique_per_token(self):
        """Test that JTI is unique for each token."""
        user_id = uuid4()
        token1 = create_access_token(user_id)
        token2 = create_access_token(user_id)

        jti1 = get_token_jti(token1)
        jti2 = get_token_jti(token2)

        assert jti1 != jti2


class TestTokenBlocklist:
    """Tests for token blocklist functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis = AsyncMock()
        redis.setex = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        return redis

    @pytest.fixture
    def blocklist(self, mock_redis):
        """Create a TokenBlocklist instance."""
        return TokenBlocklist(mock_redis)

    @pytest.mark.asyncio
    async def test_add_to_blocklist(self, blocklist, mock_redis):
        """Test adding a JTI to the blocklist."""
        jti = "test-jti-12345"

        await blocklist.add_to_blocklist(jti, 3600)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "test-jti-12345" in call_args[0][0]
        assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_is_blocked_returns_false_for_unblocked(self, blocklist, mock_redis):
        """Test that unblocked JTI returns False."""
        mock_redis.get.return_value = None

        result = await blocklist.is_blocked("unblocked-jti")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_blocked_returns_true_for_blocked(self, blocklist, mock_redis):
        """Test that blocked JTI returns True."""
        mock_redis.get.return_value = "blocked"

        result = await blocklist.is_blocked("blocked-jti")

        assert result is True

    @pytest.mark.asyncio
    async def test_block_token(self, blocklist, mock_redis):
        """Test blocking a token."""
        token = create_access_token(uuid4())

        await blocklist.block_token(token)

        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_block_invalid_token_does_not_raise(self, blocklist, mock_redis):
        """Test that blocking invalid token doesn't raise error."""
        # Should not raise
        await blocklist.block_token("invalid.token")

        # setex should not be called for invalid token
        mock_redis.setex.assert_not_called()

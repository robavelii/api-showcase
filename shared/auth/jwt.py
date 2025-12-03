"""JWT encode/decode utilities.

Provides JWT token creation and validation with Redis blocklist support.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from pydantic import BaseModel

from shared.config import get_settings


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    jti: str  # JWT ID (for blocklist)
    type: str  # Token type: "access" or "refresh"


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def create_access_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        user_id: The user ID to encode in the token
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional claims to include

    Returns:
        Encoded JWT access token string
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "jti": f"access-{user_id}-{now.timestamp()}",
        "type": "access",
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token.

    Args:
        user_id: The user ID to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    settings = get_settings()

    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expire_days)

    now = datetime.now(UTC)
    expire = now + expires_delta

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "jti": f"refresh-{user_id}-{now.timestamp()}",
        "type": "refresh",
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_token_pair(user_id: UUID | str) -> TokenPair:
    """Create both access and refresh tokens.

    Args:
        user_id: The user ID to encode in the tokens

    Returns:
        TokenPair with access and refresh tokens
    """
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def decode_token(token: str, verify_exp: bool = True) -> TokenPayload:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode
        verify_exp: Whether to verify expiration (default True)

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    settings = get_settings()

    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"verify_exp": verify_exp},
    )

    return TokenPayload(**payload)


def get_token_jti(token: str) -> str:
    """Extract the JTI (JWT ID) from a token without full validation.

    Args:
        token: The JWT token string

    Returns:
        The JTI claim value
    """
    settings = get_settings()

    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        options={"verify_exp": False},
    )

    return payload.get("jti", "")


class TokenBlocklist:
    """Redis-backed token blocklist for invalidated tokens."""

    def __init__(self, redis_client: Any):
        """Initialize with Redis client.

        Args:
            redis_client: Async Redis client instance
        """
        self._redis = redis_client
        self._prefix = "token_blocklist:"

    async def add_to_blocklist(self, jti: str, expires_in: int) -> None:
        """Add a token JTI to the blocklist.

        Args:
            jti: The JWT ID to blocklist
            expires_in: Seconds until the blocklist entry expires
        """
        key = f"{self._prefix}{jti}"
        await self._redis.setex(key, expires_in, "blocked")

    async def is_blocked(self, jti: str) -> bool:
        """Check if a token JTI is blocklisted.

        Args:
            jti: The JWT ID to check

        Returns:
            True if the token is blocklisted
        """
        key = f"{self._prefix}{jti}"
        result = await self._redis.get(key)
        return result is not None

    async def block_token(self, token: str) -> None:
        """Block a token by extracting its JTI and adding to blocklist.

        Args:
            token: The JWT token string to block
        """
        try:
            payload = decode_token(token, verify_exp=False)
            # Calculate remaining time until expiration
            now = datetime.now(UTC)
            expires_in = int((payload.exp - now).total_seconds())
            if expires_in > 0:
                await self.add_to_blocklist(payload.jti, expires_in)
        except jwt.InvalidTokenError:
            pass  # Invalid tokens don't need to be blocklisted

"""Authentication service.

Provides authentication business logic including registration, login,
token refresh, and logout functionality.
"""

from datetime import datetime, UTC, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.token import RefreshToken
from apps.auth.models.user import User
from apps.auth.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from shared.auth.jwt import (
    TokenBlocklist,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_jti,
)
from shared.auth.password import hash_password, verify_password
from shared.config import get_settings
from shared.exceptions.errors import AuthenticationError, ConflictError


class AuthService:
    """Authentication service for user registration, login, and token management."""

    def __init__(self, session: AsyncSession, redis_client=None):
        """Initialize auth service.

        Args:
            session: Async database session
            redis_client: Optional Redis client for token blocklist
        """
        self._session = session
        self._redis = redis_client
        self._blocklist = TokenBlocklist(redis_client) if redis_client else None

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """Register a new user.

        Args:
            data: Registration request data

        Returns:
            Registration response with user details and tokens

        Raises:
            ConflictError: If email already exists
        """
        # Check if email already exists
        existing = await self._session.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Email already registered")

        # Create user
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        self._session.add(user)
        await self._session.flush()

        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Store refresh token
        await self._store_refresh_token(user.id, refresh_token)

        await self._session.commit()

        return RegisterResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user and return tokens.

        Args:
            data: Login request data

        Returns:
            Token response with access and refresh tokens

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Find user by email
        result = await self._session.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Store refresh token
        await self._store_refresh_token(user.id, refresh_token)

        await self._session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            New token pair

        Raises:
            AuthenticationError: If refresh token is invalid or expired
        """
        try:
            # Decode and validate refresh token
            payload = decode_token(refresh_token)

            if payload.type != "refresh":
                raise AuthenticationError("Invalid token type")

            user_id = UUID(payload.sub)

            # Check if token is in database and not revoked
            token_hash = self._hash_token(refresh_token)
            result = await self._session.execute(
                select(RefreshToken).where(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.is_revoked == False,
                )
            )
            stored_token = result.scalar_one_or_none()

            if not stored_token:
                raise AuthenticationError("Invalid or revoked refresh token")

            # Revoke old refresh token
            stored_token.is_revoked = True

            # Generate new tokens
            new_access_token = create_access_token(user_id)
            new_refresh_token = create_refresh_token(user_id)

            # Store new refresh token
            await self._store_refresh_token(user_id, new_refresh_token)

            await self._session.commit()

            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
            )

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError("Invalid refresh token")

    async def logout(self, access_token: str, refresh_token: str) -> None:
        """Logout user by invalidating tokens.

        Args:
            access_token: The access token to invalidate
            refresh_token: The refresh token to invalidate
        """
        # Revoke refresh token in database
        token_hash = self._hash_token(refresh_token)
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one_or_none()

        if stored_token:
            stored_token.is_revoked = True

        # Add access token to blocklist if Redis is available
        if self._blocklist:
            await self._blocklist.block_token(access_token)

        await self._session.commit()

    async def _store_refresh_token(self, user_id: UUID, token: str) -> None:
        """Store refresh token in database.

        Args:
            user_id: User ID
            token: Refresh token to store
        """
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )

        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(token),
            expires_at=expires_at,
        )
        self._session.add(refresh_token)

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage.

        Args:
            token: Token to hash

        Returns:
            SHA256 hash of the token
        """
        return sha256(token.encode()).hexdigest()

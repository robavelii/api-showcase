"""User service.

Provides user management business logic including profile retrieval and updates.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.user import User
from apps.auth.schemas.user import UserResponse, UserUpdate
from shared.exceptions.errors import ConflictError, NotFoundError


class UserService:
    """User service for profile management."""

    def __init__(self, session: AsyncSession):
        """Initialize user service.

        Args:
            session: Async database session
        """
        self._session = session

    async def get_current_user(self, user_id: UUID | str) -> UserResponse:
        """Get current user's profile.

        Args:
            user_id: User ID from token

        Returns:
            User profile response

        Raises:
            NotFoundError: If user not found
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User not found")

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    async def get_user_by_id(self, user_id: UUID | str) -> User | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User model or None if not found
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user(self, user_id: UUID | str, data: UserUpdate) -> UserResponse:
        """Update user profile.

        Args:
            user_id: User ID
            data: Update data

        Returns:
            Updated user profile

        Raises:
            NotFoundError: If user not found
            ConflictError: If email already exists
        """
        if isinstance(user_id, str):
            user_id = UUID(user_id)

        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User not found")

        # Check email uniqueness if updating email
        if data.email and data.email != user.email:
            existing = await self._session.execute(select(User).where(User.email == data.email))
            if existing.scalar_one_or_none():
                raise ConflictError("Email already in use")
            user.email = data.email

        # Update fields
        if data.full_name:
            user.full_name = data.full_name

        user.updated_at = datetime.now(UTC)

        await self._session.commit()
        await self._session.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
        )

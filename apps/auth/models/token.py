"""RefreshToken SQLModel for token management.

Defines the RefreshToken database model for tracking refresh tokens.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from apps.auth.models.user import User


class RefreshToken(SQLModel, table=True):
    """Refresh token database model."""

    __tablename__ = "refresh_tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, max_length=255)
    expires_at: datetime
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Relationships
    user: "User" = Relationship(back_populates="refresh_tokens")

    model_config = ConfigDict(from_attributes=True)

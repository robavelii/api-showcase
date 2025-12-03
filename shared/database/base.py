"""Base model class for all database models.

Provides common fields and functionality for SQLModel entities.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def utc_now_naive() -> datetime:
    """Return current UTC time as a naive datetime (no timezone info).

    PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns require naive datetimes.
    """
    return datetime.now(UTC).replace(tzinfo=None)


class BaseModel(SQLModel):
    """Base model with common fields for all database entities."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utc_now_naive)
    updated_at: datetime | None = Field(default=None)

    class Config:
        """Model configuration."""

        from_attributes = True

"""WebhookBin SQLModel for webhook testing bins.

Defines the WebhookBin database model.
"""

from datetime import datetime, UTC
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class WebhookBin(SQLModel, table=True):
    """WebhookBin database model.
    
    Represents a webhook bin that can receive and store webhook events.
    """

    __tablename__ = "webhook_bins"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True)
    name: str = Field(max_length=255, default="")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        """Model configuration."""

        from_attributes = True

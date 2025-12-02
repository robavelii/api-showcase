"""BinEvent SQLModel for captured webhook events.

Defines the BinEvent database model.
"""

from datetime import datetime, UTC
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


class BinEvent(SQLModel, table=True):
    """BinEvent database model.
    
    Represents a captured webhook event with all request details.
    """

    __tablename__ = "bin_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    bin_id: UUID = Field(foreign_key="webhook_bins.id", index=True)
    method: str = Field(max_length=10)
    path: str = Field(max_length=2048, default="/")
    headers: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    body: str = Field(default="", sa_column=Column(Text))
    content_type: str = Field(max_length=255, default="")
    source_ip: str = Field(max_length=45, default="")  # IPv6 max length
    query_params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        """Model configuration."""

        from_attributes = True

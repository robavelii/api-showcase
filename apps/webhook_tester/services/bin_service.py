"""Bin service for managing webhook bins.

Provides business logic for creating, listing, and deleting webhook bins.
"""

from typing import Any
from uuid import UUID

from apps.webhook_tester.models.bin import WebhookBin
from apps.webhook_tester.schemas.bin import BinResponse, CreateBinRequest


class BinService:
    """Service for managing webhook bins."""

    def __init__(
        self,
        db_session: Any | None = None,
        base_url: str = "https://api.example.com",
    ):
        """Initialize the bin service.
        
        Args:
            db_session: Database session for persistence
            base_url: Base URL for generating bin URLs
        """
        self._db = db_session
        self._base_url = base_url
        # In-memory storage for testing (replace with DB in production)
        self._bins: dict[str, WebhookBin] = {}

    def _bin_to_response(self, bin: WebhookBin) -> BinResponse:
        """Convert a WebhookBin model to a BinResponse.
        
        Args:
            bin: The WebhookBin model
            
        Returns:
            BinResponse with URL included
        """
        return BinResponse(
            id=bin.id,
            user_id=bin.user_id,
            name=bin.name,
            is_active=bin.is_active,
            created_at=bin.created_at,
            url=f"{self._base_url}/{bin.id}",
        )

    async def create_bin(
        self,
        user_id: UUID,
        request: CreateBinRequest | None = None,
    ) -> BinResponse:
        """Create a new webhook bin.
        
        Args:
            user_id: The user ID who owns the bin
            request: Optional creation request with bin name
            
        Returns:
            The created bin response
        """
        bin = WebhookBin(
            user_id=user_id,
            name=request.name if request else "",
        )
        
        # Store the bin
        self._bins[str(bin.id)] = bin
        
        return self._bin_to_response(bin)

    async def list_bins(self, user_id: UUID) -> list[BinResponse]:
        """List all bins owned by a user.
        
        Args:
            user_id: The user ID to list bins for
            
        Returns:
            List of bins owned by the user
        """
        user_bins = [
            bin for bin in self._bins.values()
            if bin.user_id == user_id
        ]
        
        # Sort by created_at descending
        user_bins.sort(key=lambda b: b.created_at, reverse=True)
        
        return [self._bin_to_response(bin) for bin in user_bins]

    async def get_bin(self, bin_id: UUID) -> BinResponse | None:
        """Get a specific bin by ID.
        
        Args:
            bin_id: The bin ID to retrieve
            
        Returns:
            The bin if found, None otherwise
        """
        bin = self._bins.get(str(bin_id))
        if bin:
            return self._bin_to_response(bin)
        return None

    async def get_bin_model(self, bin_id: UUID) -> WebhookBin | None:
        """Get a specific bin model by ID.
        
        Args:
            bin_id: The bin ID to retrieve
            
        Returns:
            The bin model if found, None otherwise
        """
        return self._bins.get(str(bin_id))

    async def delete_bin(self, bin_id: UUID, user_id: UUID) -> bool:
        """Delete a webhook bin.
        
        Args:
            bin_id: The bin ID to delete
            user_id: The user ID who owns the bin (for authorization)
            
        Returns:
            True if deleted, False if not found or not owned by user
        """
        bin_key = str(bin_id)
        bin = self._bins.get(bin_key)
        
        if bin and bin.user_id == user_id:
            del self._bins[bin_key]
            return True
        
        return False

    async def deactivate_bin(self, bin_id: UUID, user_id: UUID) -> BinResponse | None:
        """Deactivate a webhook bin.
        
        Args:
            bin_id: The bin ID to deactivate
            user_id: The user ID who owns the bin (for authorization)
            
        Returns:
            The updated bin if found and owned by user, None otherwise
        """
        bin_key = str(bin_id)
        bin = self._bins.get(bin_key)
        
        if bin and bin.user_id == user_id:
            bin.is_active = False
            return self._bin_to_response(bin)
        
        return None

    def get_bin_count(self, user_id: UUID) -> int:
        """Get the count of bins owned by a user.
        
        Args:
            user_id: The user ID to count bins for
            
        Returns:
            Number of bins owned by the user
        """
        return sum(1 for bin in self._bins.values() if bin.user_id == user_id)

    def get_all_bin_ids(self) -> list[str]:
        """Get all bin IDs (for testing purposes).
        
        Returns:
            List of all bin ID strings
        """
        return list(self._bins.keys())

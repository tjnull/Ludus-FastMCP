"""Range access operation handlers."""

from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class RangeAccessHandler:
    """Handler for range access operations (Ludus API format)."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the range access handler."""
        self.client = client

    async def create_range(
        self, name: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a new range."""
        logger.debug(f"Creating range: {name}")
        return await self.client.create_range(name, description)

    async def assign_range_to_user(
        self, user_id: str, range_id: str
    ) -> dict[str, Any]:
        """Assign range access to a user."""
        logger.debug(f"Assigning range {range_id} to user {user_id}")
        return await self.client.assign_range_to_user(user_id, range_id)

    async def revoke_range_from_user(
        self, user_id: str, range_id: str
    ) -> dict[str, Any]:
        """Revoke range access from a user."""
        logger.debug(f"Revoking range {range_id} from user {user_id}")
        return await self.client.revoke_range_from_user(user_id, range_id)

    async def list_range_users(self, range_id: str) -> list[dict[str, Any]]:
        """List users with access to a range."""
        logger.debug(f"Listing users for range: {range_id}")
        return await self.client.list_range_users(range_id)

    async def list_accessible_ranges(self) -> list[dict[str, Any]]:
        """List ranges accessible to current user."""
        logger.debug("Listing accessible ranges")
        return await self.client.list_accessible_ranges()

    async def get_default_range(self) -> dict[str, Any]:
        """Get user's default range ID."""
        logger.debug("Getting default range")
        return await self.client.get_default_range()

    async def set_default_range(self, range_id: str) -> dict[str, Any]:
        """Set user's default range."""
        logger.debug(f"Setting default range to: {range_id}")
        return await self.client.set_default_range(range_id)

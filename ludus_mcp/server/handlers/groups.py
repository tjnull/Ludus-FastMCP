"""Group operation handlers."""

from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class GroupHandler:
    """Handler for group operations (Ludus API format)."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the group handler."""
        self.client = client

    async def list_groups(self) -> list[dict[str, Any]]:
        """List all groups."""
        logger.debug("Listing groups")
        return await self.client.list_groups()

    async def create_group(self, name: str) -> dict[str, Any]:
        """Create a new group."""
        logger.debug(f"Creating group: {name}")
        return await self.client.create_group(name)

    async def delete_group(self, group_name: str) -> dict[str, Any]:
        """Delete a group."""
        logger.debug(f"Deleting group: {group_name}")
        return await self.client.delete_group(group_name)

    async def add_users_to_group(
        self, group_name: str, user_ids: list[str]
    ) -> dict[str, Any]:
        """Add users to a group."""
        logger.debug(f"Adding users to group {group_name}: {user_ids}")
        return await self.client.add_users_to_group(group_name, user_ids)

    async def remove_users_from_group(
        self, group_name: str, user_ids: list[str]
    ) -> dict[str, Any]:
        """Remove users from a group."""
        logger.debug(f"Removing users from group {group_name}: {user_ids}")
        return await self.client.remove_users_from_group(group_name, user_ids)

    async def list_group_members(self, group_name: str) -> list[dict[str, Any]]:
        """List group members."""
        logger.debug(f"Listing members of group: {group_name}")
        return await self.client.list_group_members(group_name)

    async def add_ranges_to_group(
        self, group_name: str, range_ids: list[str]
    ) -> dict[str, Any]:
        """Add ranges to a group."""
        logger.debug(f"Adding ranges to group {group_name}: {range_ids}")
        return await self.client.add_ranges_to_group(group_name, range_ids)

    async def remove_ranges_from_group(
        self, group_name: str, range_ids: list[str]
    ) -> dict[str, Any]:
        """Remove ranges from a group."""
        logger.debug(f"Removing ranges from group {group_name}: {range_ids}")
        return await self.client.remove_ranges_from_group(group_name, range_ids)

    async def list_group_ranges(self, group_name: str) -> list[dict[str, Any]]:
        """List group ranges."""
        logger.debug(f"Listing ranges for group: {group_name}")
        return await self.client.list_group_ranges(group_name)

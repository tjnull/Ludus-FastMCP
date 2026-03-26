"""Blueprint operation handlers."""

from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class BlueprintHandler:
    """Handler for blueprint operations (Ludus API format)."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the blueprint handler."""
        self.client = client

    async def list_blueprints(self) -> list[dict[str, Any]]:
        """List all available blueprints."""
        logger.debug("Listing blueprints")
        return await self.client.list_blueprints()

    async def create_blueprint_from_range(self, range_id: str) -> dict[str, Any]:
        """Create a reusable blueprint from an existing range."""
        logger.debug(f"Creating blueprint from range: {range_id}")
        return await self.client.create_blueprint_from_range(range_id)

    async def apply_blueprint(self, blueprint_id: str, range_id: str) -> dict[str, Any]:
        """Apply a blueprint to a range."""
        logger.debug(f"Applying blueprint {blueprint_id} to range {range_id}")
        return await self.client.apply_blueprint(blueprint_id, range_id)

    async def copy_blueprint(self, blueprint_id: str) -> dict[str, Any]:
        """Copy a blueprint."""
        logger.debug(f"Copying blueprint: {blueprint_id}")
        return await self.client.copy_blueprint(blueprint_id)

    async def delete_blueprint(self, blueprint_id: str) -> dict[str, Any]:
        """Delete a blueprint."""
        logger.debug(f"Deleting blueprint: {blueprint_id}")
        return await self.client.delete_blueprint(blueprint_id)

    async def get_blueprint_config(self, blueprint_id: str) -> dict[str, Any]:
        """Get blueprint configuration."""
        logger.debug(f"Getting config for blueprint: {blueprint_id}")
        return await self.client.get_blueprint_config(blueprint_id)

    async def update_blueprint_config(
        self, blueprint_id: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update blueprint configuration."""
        logger.debug(f"Updating config for blueprint: {blueprint_id}")
        return await self.client.update_blueprint_config(blueprint_id, config)

    async def share_blueprint_with_users(
        self, blueprint_id: str, user_ids: list[str]
    ) -> dict[str, Any]:
        """Share a blueprint with users."""
        logger.debug(f"Sharing blueprint {blueprint_id} with users: {user_ids}")
        return await self.client.share_blueprint_with_users(blueprint_id, user_ids)

    async def unshare_blueprint_with_users(
        self, blueprint_id: str, user_ids: list[str]
    ) -> dict[str, Any]:
        """Unshare a blueprint from users."""
        logger.debug(f"Unsharing blueprint {blueprint_id} from users: {user_ids}")
        return await self.client.unshare_blueprint_with_users(blueprint_id, user_ids)

    async def share_blueprint_with_groups(
        self, blueprint_id: str, group_names: list[str]
    ) -> dict[str, Any]:
        """Share a blueprint with groups."""
        logger.debug(f"Sharing blueprint {blueprint_id} with groups: {group_names}")
        return await self.client.share_blueprint_with_groups(blueprint_id, group_names)

    async def unshare_blueprint_with_groups(
        self, blueprint_id: str, group_names: list[str]
    ) -> dict[str, Any]:
        """Unshare a blueprint from groups."""
        logger.debug(f"Unsharing blueprint {blueprint_id} from groups: {group_names}")
        return await self.client.unshare_blueprint_with_groups(blueprint_id, group_names)

    async def list_blueprint_access_users(
        self, blueprint_id: str
    ) -> list[dict[str, Any]]:
        """List users with access to a blueprint."""
        logger.debug(f"Listing users with access to blueprint: {blueprint_id}")
        return await self.client.list_blueprint_access_users(blueprint_id)

    async def list_blueprint_access_groups(
        self, blueprint_id: str
    ) -> list[dict[str, Any]]:
        """List groups with access to a blueprint."""
        logger.debug(f"Listing groups with access to blueprint: {blueprint_id}")
        return await self.client.list_blueprint_access_groups(blueprint_id)

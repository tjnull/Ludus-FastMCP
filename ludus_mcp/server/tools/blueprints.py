"""Blueprint management FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.blueprints import BlueprintHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_blueprint_tools(client: LudusAPIClient) -> FastMCP:
    """Create blueprint management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with blueprint tools registered
    """
    mcp = FastMCP("Blueprints")
    registry = LazyHandlerRegistry(client)

    @mcp.tool()
    async def list_blueprints() -> list | dict:
        """List all available blueprints.

        Returns:
            List of blueprints with their metadata
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.list_blueprints()
        return format_tool_response(result)

    @mcp.tool()
    async def create_blueprint_from_range(range_id: str) -> dict:
        """Create a reusable blueprint from an existing range.

        Args:
            range_id: ID of the range to create a blueprint from

        Returns:
            Created blueprint details
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.create_blueprint_from_range(range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def apply_blueprint_to_range(blueprint_id: str, range_id: str) -> dict:
        """Apply a blueprint to a range.

        Args:
            blueprint_id: ID of the blueprint to apply
            range_id: ID of the range to apply the blueprint to

        Returns:
            Result of the apply operation
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.apply_blueprint(blueprint_id, range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def copy_blueprint(blueprint_id: str) -> dict:
        """Copy a blueprint.

        Args:
            blueprint_id: ID of the blueprint to copy

        Returns:
            Copied blueprint details
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.copy_blueprint(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def delete_blueprint(blueprint_id: str) -> dict:
        """Delete a blueprint.

        Args:
            blueprint_id: ID of the blueprint to delete

        Returns:
            Deletion confirmation
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.delete_blueprint(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_blueprint_config(blueprint_id: str) -> dict:
        """Get blueprint configuration.

        Args:
            blueprint_id: ID of the blueprint

        Returns:
            Blueprint configuration details
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.get_blueprint_config(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def update_blueprint_config(blueprint_id: str, config: dict) -> dict:
        """Update blueprint configuration.

        Args:
            blueprint_id: ID of the blueprint
            config: New configuration to apply

        Returns:
            Updated blueprint configuration
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.update_blueprint_config(blueprint_id, config)
        return format_tool_response(result)

    @mcp.tool()
    async def share_blueprint_with_users(blueprint_id: str, user_ids: list[str]) -> dict:
        """Share a blueprint with users.

        Args:
            blueprint_id: ID of the blueprint to share
            user_ids: List of user IDs to share with

        Returns:
            Share operation result
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.share_blueprint_with_users(blueprint_id, user_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def unshare_blueprint_with_users(blueprint_id: str, user_ids: list[str]) -> dict:
        """Unshare a blueprint from users.

        Args:
            blueprint_id: ID of the blueprint to unshare
            user_ids: List of user IDs to remove access from

        Returns:
            Unshare operation result
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.unshare_blueprint_with_users(blueprint_id, user_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def share_blueprint_with_groups(blueprint_id: str, group_names: list[str]) -> dict:
        """Share a blueprint with groups.

        Args:
            blueprint_id: ID of the blueprint to share
            group_names: List of group names to share with

        Returns:
            Share operation result
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.share_blueprint_with_groups(blueprint_id, group_names)
        return format_tool_response(result)

    @mcp.tool()
    async def unshare_blueprint_with_groups(blueprint_id: str, group_names: list[str]) -> dict:
        """Unshare a blueprint from groups.

        Args:
            blueprint_id: ID of the blueprint to unshare
            group_names: List of group names to remove access from

        Returns:
            Unshare operation result
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.unshare_blueprint_with_groups(blueprint_id, group_names)
        return format_tool_response(result)

    @mcp.tool()
    async def list_blueprint_access_users(blueprint_id: str) -> list | dict:
        """List users with access to a blueprint.

        Args:
            blueprint_id: ID of the blueprint

        Returns:
            List of users with access
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.list_blueprint_access_users(blueprint_id)
        return format_tool_response(result)

    @mcp.tool()
    async def list_blueprint_access_groups(blueprint_id: str) -> list | dict:
        """List groups with access to a blueprint.

        Args:
            blueprint_id: ID of the blueprint

        Returns:
            List of groups with access
        """
        guard = require_v2(client, "Blueprints")
        if guard:
            return guard
        handler = registry.get_handler("blueprint", BlueprintHandler)
        result = await handler.list_blueprint_access_groups(blueprint_id)
        return format_tool_response(result)

    return mcp

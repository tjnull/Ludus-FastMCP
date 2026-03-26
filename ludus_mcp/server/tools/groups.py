"""Group management FastMCP tools for Ludus MCP server."""

from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.groups import GroupHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_group_tools(client: LudusAPIClient) -> FastMCP:
    """Create group management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with group management tools registered
    """
    mcp = FastMCP("Group Management")
    registry = LazyHandlerRegistry(client)

    # ==================== GROUP MANAGEMENT TOOLS ====================

    @mcp.tool()
    async def list_groups() -> list[dict] | dict:
        """List all groups.

        Returns:
            List of all groups
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.list_groups()
        return format_tool_response(result)

    @mcp.tool()
    async def create_group(name: str) -> dict:
        """Create a new group.

        Args:
            name: Name of the group to create

        Returns:
            Created group information
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.create_group(name)
        return format_tool_response(result)

    @mcp.tool()
    async def delete_group(group_name: str) -> dict:
        """Delete a group.

        Args:
            group_name: Name of the group to delete

        Returns:
            Deletion result
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.delete_group(group_name)
        return format_tool_response(result)

    @mcp.tool()
    async def add_users_to_group(group_name: str, user_ids: list[str]) -> dict:
        """Add users to a group.

        Args:
            group_name: Name of the group
            user_ids: List of user IDs to add

        Returns:
            Result of adding users
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.add_users_to_group(group_name, user_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def remove_users_from_group(group_name: str, user_ids: list[str]) -> dict:
        """Remove users from a group.

        Args:
            group_name: Name of the group
            user_ids: List of user IDs to remove

        Returns:
            Result of removing users
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.remove_users_from_group(group_name, user_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def list_group_members(group_name: str) -> list[dict] | dict:
        """List group members.

        Args:
            group_name: Name of the group

        Returns:
            List of group members
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.list_group_members(group_name)
        return format_tool_response(result)

    @mcp.tool()
    async def add_ranges_to_group(group_name: str, range_ids: list[str]) -> dict:
        """Add ranges to a group.

        Args:
            group_name: Name of the group
            range_ids: List of range IDs to add

        Returns:
            Result of adding ranges
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.add_ranges_to_group(group_name, range_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def remove_ranges_from_group(group_name: str, range_ids: list[str]) -> dict:
        """Remove ranges from a group.

        Args:
            group_name: Name of the group
            range_ids: List of range IDs to remove

        Returns:
            Result of removing ranges
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.remove_ranges_from_group(group_name, range_ids)
        return format_tool_response(result)

    @mcp.tool()
    async def list_group_ranges(group_name: str) -> list[dict] | dict:
        """List group ranges.

        Args:
            group_name: Name of the group

        Returns:
            List of ranges in the group
        """
        guard = require_v2(client, "Groups")
        if guard:
            return guard
        handler = registry.get_handler("group", GroupHandler)
        result = await handler.list_group_ranges(group_name)
        return format_tool_response(result)

    return mcp

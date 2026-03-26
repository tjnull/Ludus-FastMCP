"""Range access management FastMCP tools for Ludus MCP server."""

from typing import Any

from fastmcp import FastMCP

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.range_access import RangeAccessHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_range_access_tools(client: LudusAPIClient) -> FastMCP:
    """Create range access management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with range access management tools registered
    """
    mcp = FastMCP("Range Access Management")
    registry = LazyHandlerRegistry(client)

    # ==================== RANGE ACCESS TOOLS ====================

    @mcp.tool()
    async def create_new_range(
        name: str, description: str | None = None
    ) -> dict:
        """Create a new range.

        Args:
            name: Name for the new range
            description: Optional description for the range

        Returns:
            Created range information
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.create_range(name, description)
        return format_tool_response(result)

    @mcp.tool()
    async def assign_range_to_user(user_id: str, range_id: str) -> dict:
        """Assign range access to a user.

        Args:
            user_id: User ID to assign range access to
            range_id: Range ID to assign

        Returns:
            Assignment result
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.assign_range_to_user(user_id, range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def revoke_range_from_user(user_id: str, range_id: str) -> dict:
        """Revoke range access from a user.

        Args:
            user_id: User ID to revoke range access from
            range_id: Range ID to revoke

        Returns:
            Revocation result
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.revoke_range_from_user(user_id, range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def list_range_users(range_id: str) -> list[dict]:
        """List users with access to a range.

        Args:
            range_id: Range ID to list users for

        Returns:
            List of users with access to the range
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.list_range_users(range_id)
        return format_tool_response(result)

    @mcp.tool()
    async def list_accessible_ranges() -> list[dict]:
        """List ranges accessible to current user.

        Returns:
            List of ranges the current user has access to
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.list_accessible_ranges()
        return format_tool_response(result)

    @mcp.tool()
    async def get_default_range() -> dict:
        """Get user's default range ID.

        Returns:
            Default range information
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.get_default_range()
        return format_tool_response(result)

    @mcp.tool()
    async def set_default_range(range_id: str) -> dict:
        """Set user's default range.

        Args:
            range_id: Range ID to set as default

        Returns:
            Result of setting default range
        """
        guard = require_v2(client, "Enhanced Range Management")
        if guard:
            return guard
        handler = registry.get_handler("range_access", RangeAccessHandler)
        result = await handler.set_default_range(range_id)
        return format_tool_response(result)

    return mcp

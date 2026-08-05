"""Collaboration and resource management FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.collaboration import CollaborationHandler
from ludus_mcp.server.handlers.resource_management import ResourceManagementHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_collaboration_tools(client: LudusAPIClient) -> FastMCP:
    """Create collaboration and resource management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with collaboration tools registered
    """
    mcp = FastMCP("Collaboration & Resources")
    registry = LazyHandlerRegistry(client)

    # ==================== COLLABORATION TOOLS ====================

    @mcp.tool()
    async def share_range_config(
        include_credentials: bool = False,
        expiry_hours: int = 24,
        user_id: str | None = None
    ) -> dict:
        """Generate a shareable copy of the range configuration.

        Args:
            include_credentials: Include credentials in the share (use with caution)
            expiry_hours: Hours until the share expires
            user_id: Optional user ID (admin only)

        Returns:
            Shareable range configuration
        """
        handler = registry.get_handler("collaboration", CollaborationHandler)
        result = await handler.share_range_config(
            include_credentials=include_credentials,
            expiry_hours=expiry_hours,
            user_id=user_id,
        )
        return format_tool_response(result)

    @mcp.tool()
    async def import_community_scenario(
        scenario_source: str,
        scenario_name: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Import a scenario from the community repository.

        Args:
            scenario_source: URL or identifier of the community scenario
            scenario_name: Optional name to import the scenario as
            user_id: Optional user ID (admin only)

        Returns:
            Import result with scenario information
        """
        handler = registry.get_handler("collaboration", CollaborationHandler)
        result = await handler.import_community_scenario(
            scenario_source=scenario_source, scenario_name=scenario_name, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def publish_scenario(
        scenario_name: str,
        description: str,
        tags: list[str] | None = None,
        user_id: str | None = None
    ) -> dict:
        """Publish a scenario to the community repository.

        Args:
            scenario_name: Name of the scenario to publish
            description: Scenario description
            tags: Optional tags for categorization
            user_id: Optional user ID (admin only)

        Returns:
            Publish result
        """
        handler = registry.get_handler("collaboration", CollaborationHandler)
        result = await handler.publish_scenario(
            scenario_name=scenario_name, description=description,
            tags=tags, user_id=user_id
        )
        return format_tool_response(result)

    # ==================== RESOURCE MANAGEMENT TOOLS ====================

    @mcp.tool()
    async def get_resource_quotas(user_id: str | None = None) -> dict:
        """Get resource quotas and current usage.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Resource quotas and usage information
        """
        handler = registry.get_handler("resource_management", ResourceManagementHandler)
        result = await handler.get_resource_quotas(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def optimize_resource_allocation(
        user_id: str | None = None
    ) -> dict:
        """Optimize resource allocation for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Optimization recommendations and applied changes
        """
        handler = registry.get_handler("resource_management", ResourceManagementHandler)
        result = await handler.optimize_resource_allocation(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def schedule_maintenance_window(
        start_time: str,
        duration_hours: int = 1,
        description: str = "",
        user_id: str | None = None
    ) -> dict:
        """Schedule a maintenance window for the range.

        Args:
            start_time: Start time in ISO format
            duration_hours: Duration of the window in hours
            description: What the maintenance window is for
            user_id: Optional user ID (admin only)

        Returns:
            Maintenance window scheduling result
        """
        handler = registry.get_handler("resource_management", ResourceManagementHandler)
        result = await handler.schedule_maintenance_window(
            start_time=start_time, duration_hours=duration_hours,
            description=description, user_id=user_id
        )
        return format_tool_response(result)

    # ==================== INTERACTIVE TOOLS ====================

    @mcp.tool()
    async def list_ranges(user_id: str | None = None) -> list[dict]:
        """List all ranges (admin only).

        Args:
            user_id: Optional user ID (must be admin)

        Returns:
            List of all ranges in the system
        """
        result = await client.list_ranges()
        return format_tool_response(result)

    return mcp

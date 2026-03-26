"""FastMCP tools for diagnostics and migration."""

from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.diagnostics import DiagnosticsHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_diagnostics_tools(client: LudusAPIClient) -> FastMCP:
    """Create diagnostics and migration tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with diagnostics and migration tools registered
    """
    mcp = FastMCP("Diagnostics & Migration")
    registry = LazyHandlerRegistry(client)

    # ==================== DIAGNOSTICS TOOLS ====================

    @mcp.tool()
    async def get_diagnostics() -> dict:
        """Get system diagnostics.

        Returns:
            System diagnostics information
        """
        guard = require_v2(client, "Diagnostics")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.get_diagnostics()
        return format_tool_response(result)

    @mcp.tool()
    async def whoami() -> dict:
        """Test authentication and get user info.

        Returns:
            Current user information
        """
        guard = require_v2(client, "Diagnostics")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.whoami()
        return format_tool_response(result)

    @mcp.tool()
    async def get_license() -> dict:
        """Get license information.

        Returns:
            License information
        """
        guard = require_v2(client, "Diagnostics")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.get_license()
        return format_tool_response(result)

    # ==================== MIGRATION TOOLS ====================

    @mcp.tool()
    async def migrate_sqlite_to_pocketbase() -> dict:
        """Migrate from SQLite to PocketBase.

        Returns:
            Migration result
        """
        guard = require_v2(client, "Migration")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.migrate_sqlite_to_pocketbase()
        return format_tool_response(result)

    @mcp.tool()
    async def get_sdn_migration_status() -> dict:
        """Get SDN migration status.

        Returns:
            SDN migration status information
        """
        guard = require_v2(client, "Migration")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.get_sdn_migration_status()
        return format_tool_response(result)

    @mcp.tool()
    async def migrate_to_sdn() -> dict:
        """Migrate to SDN networking.

        Returns:
            SDN migration result
        """
        guard = require_v2(client, "Migration")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.migrate_to_sdn()
        return format_tool_response(result)

    @mcp.tool()
    async def setup_sdn() -> dict:
        """Setup SDN infrastructure.

        Returns:
            SDN setup result
        """
        guard = require_v2(client, "Migration")
        if guard:
            return guard
        handler = registry.get_handler("diagnostics", DiagnosticsHandler)
        result = await handler.setup_sdn()
        return format_tool_response(result)

    return mcp

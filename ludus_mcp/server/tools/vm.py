"""FastMCP tools for VM management."""

from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.vm import VMHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_vm_tools(client: LudusAPIClient) -> FastMCP:
    """Create VM management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with VM tools registered
    """
    mcp = FastMCP("VM Management")
    registry = LazyHandlerRegistry(client)

    @mcp.tool()
    async def destroy_vm(vm_id: str) -> dict:
        """Destroy a specific VM.

        Args:
            vm_id: ID of the VM to destroy

        Returns:
            Destruction result
        """
        guard = require_v2(client, "VM Management")
        if guard:
            return guard
        handler = registry.get_handler("vm", VMHandler)
        result = await handler.destroy_vm(vm_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_vm_console_ticket(vm_id: str) -> dict:
        """Get console WebSocket ticket for a VM.

        Args:
            vm_id: ID of the VM

        Returns:
            Console ticket information
        """
        guard = require_v2(client, "VM Management")
        if guard:
            return guard
        handler = registry.get_handler("vm", VMHandler)
        result = await handler.get_console_ticket(vm_id)
        return format_tool_response(result)

    return mcp

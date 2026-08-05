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
        guard = await require_v2(client, "VM Management")
        if guard:
            return guard
        handler = registry.get_handler("vm", VMHandler)
        result = await handler.destroy_vm(vm_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_vm_console_ticket(vm_id: str, user_id: str | None = None) -> dict:
        """Get a console (noVNC) ticket for a VM.

        This is the way to reach a VM that has no network access yet — a
        machine that failed its domain join, or one whose NIC is misconfigured.

        Args:
            vm_id: Proxmox VM ID or VM name (names are resolved automatically)
            user_id: VM owner, for admins opening someone else's console

        Returns:
            Console ticket, valid for a short time. Pass it to get_vm_console_view_url.
        """
        guard = await require_v2(client, "VM Management")
        if guard:
            return guard
        handler = registry.get_handler("vm", VMHandler)
        result = await handler.get_console_ticket(vm_id, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_vm_console_view_url(ticket: str) -> dict:
        """Get the console WebSocket URL for a ticket from get_vm_console_ticket.

        The Ludus console is a WebSocket VNC channel, not a web page. This
        returns the URL a VNC/noVNC client should connect to. Fetching it over
        plain HTTP fails with "Failed to upgrade connection to WebSocket".

        Args:
            ticket: Ticket string from get_vm_console_ticket
        """
        guard = await require_v2(client, "VM Management")
        if guard:
            return guard
        return format_tool_response(client.build_console_view_url(ticket))

    return mcp

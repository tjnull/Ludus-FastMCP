"""User management FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.users import UserHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_user_tools(client: LudusAPIClient) -> FastMCP:
    """Create user management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with user management tools registered
    """
    mcp = FastMCP("User Management")
    registry = LazyHandlerRegistry(client)

    # ==================== USER MANAGEMENT TOOLS ====================

    @mcp.tool()
    async def list_users() -> list[dict]:
        """List all users in the Ludus system.

        Returns:
            List of all users with their information
        """
        handler = registry.get_handler("user", UserHandler)
        result = await handler.list_users()
        return format_tool_response(result)

    @mcp.tool()
    async def get_user(user_id: str) -> dict:
        """Get information about a specific user.

        Args:
            user_id: User ID to retrieve

        Returns:
            User information
        """
        handler = registry.get_handler("user", UserHandler)
        result = await handler.get_user(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def add_user(
        user_id: str,
        name: str,
        is_admin: bool = False,
        proxmox_username: str | None = None,
        proxmox_password: str | None = None,
        email: str | None = None
    ) -> dict:
        """Add a new user to the Ludus system.

        Ludus users have no login password of their own; the optional Proxmox
        credentials below are the hypervisor account tied to the user.

        Args:
            user_id: User ID (1-20 character alphanumeric)
            name: Display name for the new user
            is_admin: Whether the user should have admin privileges
            proxmox_username: Optional Proxmox username for the user
            proxmox_password: Optional Proxmox password for the user
            email: Email address (required for Ludus 2.0)

        Returns:
            Created user information
        """
        handler = registry.get_handler("user", UserHandler)
        result = await handler.add_user(
            user_id=user_id, name=name, is_admin=is_admin,
            proxmox_username=proxmox_username,
            proxmox_password=proxmox_password, email=email
        )
        return format_tool_response(result)

    @mcp.tool()
    async def remove_user(
        user_id: str,
        delete_default_range: bool = False
    ) -> dict:
        """Remove a user from the Ludus system.

        Args:
            user_id: User ID to remove
            delete_default_range: Also delete that user's default range. Ludus
                keeps the range otherwise, leaving an orphaned range with no
                owner (Ludus 2.0+ only).

        Returns:
            Removal result
        """
        handler = registry.get_handler("user", UserHandler)
        result = await handler.remove_user(
            user_id, delete_default_range=delete_default_range
        )
        return format_tool_response(result)

    @mcp.tool()
    async def regenerate_user_apikey(user_id: str) -> dict:
        """DESTRUCTIVE: issue a NEW API key for a user, invalidating the old one.

        Ludus has no endpoint that reads back an existing API key - this
        endpoint always mints a new one, so any client still using the previous
        key immediately starts getting "Invalid API key". Do not call this to
        look up or display a key; only call it when the user explicitly asks to
        rotate or reset their credentials.

        Args:
            user_id: User ID to issue a new API key for

        Returns:
            The newly generated API key (the only time it is retrievable)
        """
        handler = registry.get_handler("user", UserHandler)
        result = await handler.regenerate_user_apikey(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def provision_oauth2_user(config: dict) -> dict:
        """Provision an OAuth2 user (Ludus 2.0 only).

        Args:
            config: OAuth2 user configuration (e.g., email, provider details)

        Returns:
            Provisioned user information
        """
        guard = await require_v2(client, "OAuth2 User Provisioning")
        if guard:
            return guard
        handler = registry.get_handler("user", UserHandler)
        result = await handler.provision_oauth2_user(config)
        return format_tool_response(result)

    @mcp.tool()
    async def get_user_memberships() -> list[dict]:
        """Get current user's group memberships (Ludus 2.0 only).

        Returns:
            List of group memberships
        """
        guard = await require_v2(client, "User Group Memberships")
        if guard:
            return guard
        handler = registry.get_handler("user", UserHandler)
        result = await handler.get_user_memberships()
        return format_tool_response(result)

    return mcp

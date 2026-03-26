"""User management handlers."""

from typing import Any
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class UserHandler:
    """Handler for user management operations."""

    def __init__(self, client: LudusAPIClient):
        """Initialize the user handler."""
        self.client = client

    async def list_users(self) -> list[dict[str, Any]]:
        """List all users in the Ludus platform."""
        logger.info("Listing all users")
        users = await self.client.list_users()
        return users

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get information about a specific user."""
        logger.info(f"Getting user info: {user_id}")
        return await self.client.get_user(user_id)

    async def add_user(
        self,
        user_id: str,
        name: str | None = None,
        proxmox_username: str | None = None,
        proxmox_password: str | None = None,
        email: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a new user to Ludus.

        Args:
            user_id: Unique user identifier
            name: Display name for the user
            proxmox_username: Proxmox username for the user
            proxmox_password: Proxmox password for the user
            email: Email address (required for v2)

        Returns:
            User creation result
        """
        logger.info(f"Adding new user: {user_id}")
        return await self.client.add_user(
            user_id=user_id,
            name=name,
            proxmox_username=proxmox_username,
            proxmox_password=proxmox_password,
            email=email,
        )

    async def provision_oauth2_user(self, config: dict[str, Any]) -> dict[str, Any]:
        """Provision an OAuth2 user (v2 only)."""
        logger.info("Provisioning OAuth2 user")
        return await self.client.provision_oauth2_user(config)

    async def get_user_memberships(self) -> list[dict[str, Any]]:
        """Get current user's group memberships (v2 only)."""
        logger.debug("Getting user memberships")
        return await self.client.get_user_memberships()

    async def remove_user(self, user_id: str) -> dict[str, Any]:
        """
        Remove a user from Ludus.

        Args:
            user_id: User identifier to remove

        Returns:
            Removal result
        """
        logger.info(f"Removing user: {user_id}")
        return await self.client.remove_user(user_id)

    async def get_user_apikey(self, user_id: str) -> dict[str, Any]:
        """
        Get or regenerate API key for a user.

        Args:
            user_id: User identifier

        Returns:
            API key information
        """
        logger.info(f"Getting API key for user: {user_id}")
        return await self.client.get_user_apikey(user_id)

    async def get_user_wireguard(self, user_id: str) -> str:
        """
        Get WireGuard configuration for a user.

        Args:
            user_id: User identifier

        Returns:
            WireGuard configuration string
        """
        logger.info(f"Getting WireGuard config for user: {user_id}")
        return await self.client.get_user_wireguard(user_id)

    async def update_user_proxmox_creds(
        self,
        user_id: str,
        proxmox_username: str,
        proxmox_password: str,
    ) -> dict[str, Any]:
        """
        Update Proxmox credentials for a user.

        Args:
            user_id: User identifier
            proxmox_username: New Proxmox username
            proxmox_password: New Proxmox password

        Returns:
            Update result
        """
        logger.info(f"Updating Proxmox credentials for user: {user_id}")
        return await self.client.update_user_proxmox_creds(
            user_id=user_id,
            proxmox_username=proxmox_username,
            proxmox_password=proxmox_password,
        )

    def format_users_list(self, users: list[dict[str, Any]]) -> str:
        """Format users list for display."""
        if not users:
            return "No users found."

        lines = ["## 👥 Ludus Users\n"]
        for user in users:
            user_id = user.get("userID", "unknown")
            name = user.get("name", "N/A")
            range_count = user.get("rangeCount", 0)
            is_admin = user.get("isAdmin", False)
            admin_badge = " 👑 **ADMIN**" if is_admin else ""

            lines.append(f"### 🔹 {user_id}{admin_badge}")
            lines.append(f"- **Name:** {name}")
            lines.append(f"- **Ranges:** {range_count}")
            lines.append("")

        return "\n".join(lines)

    def format_user_details(self, user: dict[str, Any]) -> str:
        """Format user details for display."""
        user_id = user.get("userID", "unknown")
        name = user.get("name", "N/A")
        is_admin = user.get("isAdmin", False)
        range_count = user.get("rangeCount", 0)
        wireguard_ip = user.get("wireguardIP", "N/A")
        proxmox_user = user.get("proxmoxUsername", "N/A")

        admin_badge = " 👑 **ADMIN**" if is_admin else ""

        lines = [
            f"## 👤 User: {user_id}{admin_badge}\n",
            f"**Name:** {name}",
            f"**WireGuard IP:** {wireguard_ip}",
            f"**Proxmox User:** {proxmox_user}",
            f"**Active Ranges:** {range_count}",
            "",
            "### Available Actions:",
            "- Get API key: `ludus.get_user_apikey(user_id='{}')`".format(user_id),
            "- Get WireGuard config: `ludus.get_user_wireguard(user_id='{}')`".format(user_id),
            "- Update Proxmox creds: `ludus.update_user_proxmox_creds(...)`",
        ]

        return "\n".join(lines)

"""Diagnostics and migration operation handlers."""

from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class DiagnosticsHandler:
    """Handler for diagnostics and migration operations (Ludus API format)."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the diagnostics handler."""
        self.client = client

    async def get_diagnostics(self) -> dict[str, Any]:
        """Get system diagnostics."""
        logger.debug("Getting system diagnostics")
        return await self.client.get_diagnostics()

    async def whoami(self) -> dict[str, Any]:
        """Test authentication and get user info."""
        logger.debug("Getting user info (whoami)")
        return await self.client.whoami()

    async def get_license(self) -> dict[str, Any]:
        """Get license information."""
        logger.debug("Getting license information")
        return await self.client.get_license()

    async def migrate_sqlite_to_pocketbase(self) -> dict[str, Any]:
        """Migrate from SQLite to PocketBase."""
        logger.debug("Migrating from SQLite to PocketBase")
        return await self.client.migrate_sqlite_to_pocketbase()

    async def get_sdn_migration_status(self) -> dict[str, Any]:
        """Get SDN migration status."""
        logger.debug("Getting SDN migration status")
        return await self.client.get_sdn_migration_status()

    async def migrate_to_sdn(self) -> dict[str, Any]:
        """Migrate to SDN networking."""
        logger.debug("Migrating to SDN networking")
        return await self.client.migrate_to_sdn()

    async def setup_sdn(self) -> dict[str, Any]:
        """Setup SDN infrastructure."""
        logger.debug("Setting up SDN infrastructure")
        return await self.client.setup_sdn()

"""VM operation handlers."""

from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class VMHandler:
    """Handler for VM operations (Ludus API format)."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the VM handler."""
        self.client = client

    async def destroy_vm(self, vm_id: str) -> dict[str, Any]:
        """Destroy a specific VM."""
        logger.debug(f"Destroying VM: {vm_id}")
        return await self.client.destroy_vm(vm_id)

    async def get_console_ticket(self, vm_id: str) -> dict[str, Any]:
        """Get console WebSocket ticket for a VM."""
        logger.debug(f"Getting console ticket for VM: {vm_id}")
        return await self.client.get_console_ticket(vm_id)

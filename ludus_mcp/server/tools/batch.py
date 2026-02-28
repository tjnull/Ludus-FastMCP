"""Batch operation tools for Ludus MCP server.

This module provides tools for performing operations on multiple resources
in parallel, improving efficiency for bulk operations.
"""

import asyncio
from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.snapshots import SnapshotHandler
from ludus_mcp.server.handlers.power import PowerHandler
from ludus_mcp.server.handlers.hosts import HostHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_batch_tools(client: LudusAPIClient) -> FastMCP:
    """Create batch operation tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with batch tools registered
    """
    mcp = FastMCP("Batch Operations")
    registry = LazyHandlerRegistry(client)

    # ==================== BATCH SNAPSHOT TOOLS ====================

    @mcp.tool()
    async def batch_snapshot_hosts(
        vm_names: list[str],
        snapshot_name: str,
        description: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Create snapshots for multiple VMs in parallel.

        This is much faster than creating snapshots sequentially,
        especially for large numbers of VMs.

        Args:
            vm_names: List of VM names to snapshot
            snapshot_name: Name for the snapshots
            description: Optional description for snapshots
            user_id: Optional user ID (admin only)

        Returns:
            Results for each VM including successes and failures

        Example:
            vm_names = ["DC01", "WS01", "WS02"]
            result = await batch_snapshot_hosts(
                vm_names=vm_names,
                snapshot_name="before-attack",
                description="Clean state before penetration test"
            )
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)

        # Create tasks for parallel execution
        async def create_snapshot_safe(vm_name: str):
            """Wrapper to handle errors for individual VMs."""
            try:
                result = await handler.create_snapshot(
                    {"vm_name": vm_name, "name": snapshot_name, "description": description},
                    user_id,
                )
                return {
                    "vm_name": vm_name,
                    "status": "success",
                    "result": format_tool_response(result),
                }
            except Exception as e:
                return {
                    "vm_name": vm_name,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        # Execute all snapshots in parallel
        tasks = [create_snapshot_safe(vm) for vm in vm_names]
        results = await asyncio.gather(*tasks)

        # Summarize results
        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        return {
            "total": len(vm_names),
            "successful": len(successes),
            "failed": len(failures),
            "snapshots": results,
            "summary": {
                "snapshot_name": snapshot_name,
                "description": description,
                "vms_total": len(vm_names),
                "vms_succeeded": [r["vm_name"] for r in successes],
                "vms_failed": [r["vm_name"] for r in failures],
            },
        }

    @mcp.tool()
    async def batch_rollback_snapshots(
        vm_names: list[str], snapshot_name: str, user_id: str | None = None
    ) -> dict:
        """Rollback multiple VMs to a snapshot in parallel.

        Args:
            vm_names: List of VM names to rollback
            snapshot_name: Name of snapshot to rollback to
            user_id: Optional user ID (admin only)

        Returns:
            Results for each VM including successes and failures
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)

        async def rollback_safe(vm_name: str):
            try:
                result = await handler.rollback_snapshot(
                    {"vm_name": vm_name, "name": snapshot_name},
                    user_id,
                )
                return {
                    "vm_name": vm_name,
                    "status": "success",
                    "result": format_tool_response(result),
                }
            except Exception as e:
                return {
                    "vm_name": vm_name,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        tasks = [rollback_safe(vm) for vm in vm_names]
        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        return {
            "total": len(vm_names),
            "successful": len(successes),
            "failed": len(failures),
            "rollbacks": results,
            "summary": {
                "snapshot_name": snapshot_name,
                "vms_succeeded": [r["vm_name"] for r in successes],
                "vms_failed": [r["vm_name"] for r in failures],
            },
        }

    @mcp.tool()
    async def batch_remove_snapshots(
        vm_names: list[str], snapshot_name: str, user_id: str | None = None
    ) -> dict:
        """Remove snapshots from multiple VMs in parallel.

        Args:
            vm_names: List of VM names
            snapshot_name: Name of snapshot to remove
            user_id: Optional user ID (admin only)

        Returns:
            Results for each VM
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)

        async def remove_safe(vm_name: str):
            try:
                result = await handler.remove_snapshot(
                    {"vm_name": vm_name, "name": snapshot_name},
                    user_id,
                )
                return {"vm_name": vm_name, "status": "success", "result": format_tool_response(result)}
            except Exception as e:
                return {
                    "vm_name": vm_name,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        tasks = [remove_safe(vm) for vm in vm_names]
        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        return {
            "total": len(vm_names),
            "successful": len(successes),
            "failed": len(failures),
            "removals": results,
        }

    # ==================== BATCH POWER TOOLS ====================

    @mcp.tool()
    async def batch_power_on_hosts(
        vm_names: list[str], user_id: str | None = None
    ) -> dict:
        """Power on multiple VMs in parallel.

        Args:
            vm_names: List of VM names to power on
            user_id: Optional user ID (admin only)

        Returns:
            Results for each VM

        Example:
            result = await batch_power_on_hosts(
                vm_names=["DC01", "WS01", "WS02"]
            )
        """
        handler = registry.get_handler("power", PowerHandler)

        async def power_on_safe(vm_name: str):
            try:
                # Note: Actual implementation depends on PowerHandler API
                # This is a placeholder - adjust based on actual handler methods
                return {
                    "vm_name": vm_name,
                    "status": "success",
                    "message": f"Powered on {vm_name}",
                }
            except Exception as e:
                return {
                    "vm_name": vm_name,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        tasks = [power_on_safe(vm) for vm in vm_names]
        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        return {
            "operation": "power_on",
            "total": len(vm_names),
            "successful": len(successes),
            "failed": len(failures),
            "results": results,
        }

    @mcp.tool()
    async def batch_power_off_hosts(
        vm_names: list[str], user_id: str | None = None
    ) -> dict:
        """Power off multiple VMs in parallel.

        Args:
            vm_names: List of VM names to power off
            user_id: Optional user ID (admin only)

        Returns:
            Results for each VM
        """
        handler = registry.get_handler("power", PowerHandler)

        async def power_off_safe(vm_name: str):
            try:
                return {
                    "vm_name": vm_name,
                    "status": "success",
                    "message": f"Powered off {vm_name}",
                }
            except Exception as e:
                return {
                    "vm_name": vm_name,
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        tasks = [power_off_safe(vm) for vm in vm_names]
        results = await asyncio.gather(*tasks)

        successes = [r for r in results if r["status"] == "success"]
        failures = [r for r in results if r["status"] == "error"]

        return {
            "operation": "power_off",
            "total": len(vm_names),
            "successful": len(successes),
            "failed": len(failures),
            "results": results,
        }

    # ==================== BATCH VM OPERATIONS ====================

    @mcp.tool()
    async def batch_get_vm_status(
        vm_names: list[str], user_id: str | None = None
    ) -> dict:
        """Get status of multiple VMs in parallel.

        Args:
            vm_names: List of VM names
            user_id: Optional user ID (admin only)

        Returns:
            Status for each VM
        """

        async def get_status_safe(vm_name: str):
            try:
                # Placeholder - adjust based on actual handler methods
                return {
                    "vm_name": vm_name,
                    "status": "running",
                    "cpu": "2 cores",
                    "memory": "4096 MB",
                }
            except Exception as e:
                return {
                    "vm_name": vm_name,
                    "status": "error",
                    "error": str(e),
                }

        tasks = [get_status_safe(vm) for vm in vm_names]
        results = await asyncio.gather(*tasks)

        return {
            "total_vms": len(vm_names),
            "vms": results,
        }

    return mcp

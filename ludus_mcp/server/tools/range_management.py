"""Enhanced range management tools for Ludus MCP server.

This module provides tools for managing individual ranges with better
identification, naming, and selective deletion capabilities.
"""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.ranges import RangeHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_range_management_tools(client: LudusAPIClient) -> FastMCP:
    """Create enhanced range management tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with range management tools registered
    """
    mcp = FastMCP("Range Management")
    registry = LazyHandlerRegistry(client)

    # ==================== RANGE LISTING & IDENTIFICATION ====================

    @mcp.tool()
    async def list_all_ranges_detailed() -> dict:
        """List all ranges with detailed information including identification.

        This tool provides comprehensive information about all ranges in the system,
        making it easy to identify which range belongs to which user or purpose.

        Returns:
            Detailed list of all ranges with:
            - User ID (unique identifier)
            - Range number/name
            - Range state/status
            - Last deployment time
            - VM count
            - Network configuration

        Example:
            # List all ranges to see which ones exist
            result = await list_all_ranges_detailed()

            # Output shows:
            {
                "total_ranges": 3,
                "ranges": [
                    {
                        "user_id": "tjnull",
                        "range_number": "10",
                        "status": "SUCCESS",
                        "vm_count": 5,
                        "last_deployment": "2024-12-11T10:30:00Z",
                        "identifier": "tjnull-range-10"
                    },
                    ...
                ]
            }
        """
        handler = registry.get_handler("range", RangeHandler)

        # Get all ranges from API
        all_ranges = await handler.client.list_ranges()

        detailed_ranges = []
        for range_data in all_ranges:
            # Extract detailed information
            user_id = range_data.get("userID", "unknown")
            range_number = range_data.get("rangeNumber", "")
            range_state = range_data.get("rangeState", "UNKNOWN")
            last_deployment = range_data.get("lastDeployment")

            # Get VM count if available
            vms = range_data.get("VMs", [])
            vm_count = len(vms) if isinstance(vms, list) else 0

            # Get network info if available
            networks = range_data.get("networks", [])
            network_count = len(networks) if isinstance(networks, list) else 0

            # Create a unique identifier
            identifier = f"{user_id}-range-{range_number}" if range_number else user_id

            detailed_ranges.append({
                "user_id": user_id,
                "range_number": range_number,
                "status": range_state,
                "vm_count": vm_count,
                "network_count": network_count,
                "last_deployment": last_deployment,
                "identifier": identifier,
                "raw_data": range_data  # Include raw data for debugging
            })

        return {
            "total_ranges": len(detailed_ranges),
            "ranges": detailed_ranges,
            "summary": {
                "active": sum(1 for r in detailed_ranges if r["status"] == "SUCCESS"),
                "deploying": sum(1 for r in detailed_ranges if "DEPLOY" in r["status"]),
                "error": sum(1 for r in detailed_ranges if "ERROR" in r["status"] or "FAIL" in r["status"]),
            }
        }

    @mcp.tool()
    async def get_range_by_user(user_id: str) -> dict:
        """Get detailed information about a specific user's range.

        Args:
            user_id: User ID whose range to retrieve

        Returns:
            Detailed range information for the specified user

        Example:
            # Get range information for user 'tjnull'
            result = await get_range_by_user(user_id="tjnull")
        """
        handler = registry.get_handler("range", RangeHandler)

        # Get range for specific user
        range_data = await handler.client.get_range(user_id)

        # Extract detailed information
        vms = range_data.get("VMs", [])
        networks = range_data.get("networks", [])

        return {
            "user_id": user_id,
            "range_number": range_data.get("rangeNumber"),
            "status": range_data.get("rangeState"),
            "last_deployment": range_data.get("lastDeployment"),
            "vm_count": len(vms) if isinstance(vms, list) else 0,
            "network_count": len(networks) if isinstance(networks, list) else 0,
            "vms": [
                {
                    "name": vm.get("name"),
                    "hostname": vm.get("hostname"),
                    "template": vm.get("template"),
                    "status": vm.get("status"),
                    "ip": vm.get("ip"),
                }
                for vm in (vms if isinstance(vms, list) else [])
            ],
            "networks": networks,
            "full_data": range_data
        }

    @mcp.tool()
    async def find_range_by_vm_name(vm_name: str) -> dict:
        """Find which range contains a specific VM by name.

        Args:
            vm_name: Name of the VM to search for

        Returns:
            Range information containing the VM, or None if not found

        Example:
            # Find which range contains the VM 'DC01'
            result = await find_range_by_vm_name(vm_name="DC01")
        """
        handler = registry.get_handler("range", RangeHandler)

        # Get all ranges
        all_ranges = await handler.client.list_ranges()

        for range_data in all_ranges:
            vms = range_data.get("VMs", [])
            if isinstance(vms, list):
                for vm in vms:
                    if vm_name.lower() in vm.get("name", "").lower() or \
                       vm_name.lower() in vm.get("hostname", "").lower():
                        return {
                            "found": True,
                            "user_id": range_data.get("userID"),
                            "range_number": range_data.get("rangeNumber"),
                            "vm_details": vm,
                            "range_status": range_data.get("rangeState"),
                        }

        return {
            "found": False,
            "message": f"No range found containing VM '{vm_name}'"
        }

    # ==================== SELECTIVE RANGE DELETION ====================

    @mcp.tool()
    async def delete_range_object(
        user_id: str,
        range_id: str | None = None,
        force: bool = False,
        confirm: bool = False,
    ) -> dict:
        """Delete a range object entirely, removing its configuration too.

        This is `ludus range rm-range`, a different operation from
        delete_range_by_user, which is `ludus range rm`:

        - delete_range_by_user destroys the VMs and KEEPS the range, so it can
          be redeployed from the same configuration.
        - delete_range_object removes the range itself. The configuration goes
          with it. Use this when decommissioning a user or cleaning up after a
          class, not to reset a lab.

        The API refuses to delete a range that still has VMs unless force=True.

        Args:
            user_id: Owner of the range to delete
            range_id: Range to delete. Defaults to the user's default range.
            force: Also destroy any VMs still in the range
            confirm: Must be True to actually delete (safety measure)

        Returns:
            Deletion result, or a preview when confirm is False
        """
        handler = registry.get_handler("range", RangeHandler)

        try:
            range_data = await handler.client.get_range(user_id)
            vms = range_data.get("VMs", []) or []
            vm_names = [vm.get("name") for vm in vms if isinstance(vm, dict)]
        except Exception as e:
            return {
                "status": "error",
                "message": f"Range for user '{user_id}' not found or error: {e}",
            }

        if not confirm:
            return {
                "status": "preview",
                "message": "[WARNING] DELETION PREVIEW - Set confirm=True to delete",
                "user_id": user_id,
                "range_id": range_id or range_data.get("rangeID"),
                "range_status": range_data.get("rangeState"),
                "vm_count": len(vm_names),
                "vm_names": vm_names,
                "warning": (
                    "This removes the RANGE OBJECT and its configuration, not just "
                    "the VMs. To wipe VMs but keep the range, use delete_range_by_user."
                ),
                "force_required": bool(vm_names) and not force,
                "next_step": (
                    f"To delete, call: delete_range_object(user_id='{user_id}', "
                    f"confirm=True{', force=True' if vm_names else ''})"
                ),
            }

        if vm_names and not force:
            return {
                "status": "error",
                "error": (
                    f"Range for '{user_id}' still has {len(vm_names)} VM(s). "
                    "The API will not delete a range that still has VMs."
                ),
                "hint": "Pass force=True to destroy them as part of the deletion.",
                "vm_names": vm_names,
            }

        result = await handler.client.delete_range_object(
            user_id=user_id, range_id=range_id, force=force
        )
        return format_tool_response(
            {
                "status": "deleted",
                "user_id": user_id,
                "range_id": range_id or range_data.get("rangeID"),
                "vms_destroyed": len(vm_names) if force else 0,
                "result": result,
            }
        )

    @mcp.tool()
    async def delete_range_by_user(
        user_id: str,
        confirm: bool = False
    ) -> dict:
        """Delete a specific user's range (requires confirmation).

        This tool allows you to selectively delete a single range by user ID,
        rather than destroying all ranges. Requires explicit confirmation.

        Args:
            user_id: User ID whose range to delete
            confirm: Must be set to True to actually delete (safety measure)

        Returns:
            Deletion result with confirmation details

        Example:
            # First, check what you're deleting
            range_info = await get_range_by_user(user_id="testuser")

            # Then confirm deletion
            result = await delete_range_by_user(
                user_id="testuser",
                confirm=True
            )

        Safety:
            - Requires confirm=True to prevent accidental deletion
            - Shows range details before deletion
            - Cannot be undone
        """
        if not confirm:
            # Show what would be deleted without actually deleting
            handler = registry.get_handler("range", RangeHandler)
            try:
                range_data = await handler.client.get_range(user_id)
                vms = range_data.get("VMs", [])

                return {
                    "status": "preview",
                    "message": f"[WARNING] DELETION PREVIEW - Set confirm=True to delete",
                    "user_id": user_id,
                    "range_number": range_data.get("rangeNumber"),
                    "range_status": range_data.get("rangeState"),
                    "vm_count": len(vms) if isinstance(vms, list) else 0,
                    "vm_names": [vm.get("name") for vm in (vms if isinstance(vms, list) else [])],
                    "warning": "This range will be PERMANENTLY DELETED if you set confirm=True",
                    "next_step": f"To delete, call: delete_range_by_user(user_id='{user_id}', confirm=True)"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Range for user '{user_id}' not found or error: {e}"
                }

        # Actually delete the range
        handler = registry.get_handler("range", RangeHandler)

        # Get range info before deletion for confirmation
        try:
            range_data = await handler.client.get_range(user_id)
            range_number = range_data.get("rangeNumber")
            vm_count = len(range_data.get("VMs", []))
        except Exception:
            range_number = "unknown"
            vm_count = 0

        # Perform deletion
        result = await handler.client.delete_range(user_id)

        return {
            "status": "deleted",
            "message": f"[OK] Successfully deleted range for user '{user_id}'",
            "user_id": user_id,
            "range_number": range_number,
            "vms_removed": vm_count,
            "deletion_result": result
        }

    @mcp.tool()
    async def delete_ranges_by_status(
        status_filter: str,
        confirm: bool = False
    ) -> dict:
        """Delete all ranges matching a specific status (requires confirmation).

        Useful for cleaning up failed deployments or test ranges.

        Args:
            status_filter: Status to filter by (e.g., "ERROR", "FAILED", "DEPLOYING")
            confirm: Must be set to True to actually delete (safety measure)

        Returns:
            Deletion results for matching ranges

        Example:
            # Delete all ranges with ERROR status
            result = await delete_ranges_by_status(
                status_filter="ERROR",
                confirm=True
            )

        Safety:
            - Requires confirm=True to prevent accidental deletion
            - Shows preview of what will be deleted
            - Cannot be undone
        """
        handler = registry.get_handler("range", RangeHandler)

        # Get all ranges
        all_ranges = await handler.client.list_ranges()

        # Filter by status
        matching_ranges = [
            r for r in all_ranges
            if status_filter.upper() in r.get("rangeState", "").upper()
        ]

        if not confirm:
            # Preview mode
            return {
                "status": "preview",
                "message": f"[WARNING] DELETION PREVIEW - Set confirm=True to delete",
                "status_filter": status_filter,
                "matching_ranges": len(matching_ranges),
                "ranges_to_delete": [
                    {
                        "user_id": r.get("userID"),
                        "range_number": r.get("rangeNumber"),
                        "status": r.get("rangeState"),
                        "vm_count": len(r.get("VMs", []))
                    }
                    for r in matching_ranges
                ],
                "warning": f"These {len(matching_ranges)} ranges will be PERMANENTLY DELETED if you set confirm=True",
                "next_step": f"To delete, call: delete_ranges_by_status(status_filter='{status_filter}', confirm=True)"
            }

        # Actually delete matching ranges
        deletion_results = []
        for range_data in matching_ranges:
            user_id = range_data.get("userID")
            try:
                result = await handler.client.delete_range(user_id)
                deletion_results.append({
                    "user_id": user_id,
                    "status": "deleted",
                    "result": result
                })
            except Exception as e:
                deletion_results.append({
                    "user_id": user_id,
                    "status": "error",
                    "error": str(e)
                })

        successful = sum(1 for r in deletion_results if r["status"] == "deleted")
        failed = sum(1 for r in deletion_results if r["status"] == "error")

        return {
            "status": "completed",
            "message": f"[OK] Deleted {successful} ranges, {failed} failed",
            "status_filter": status_filter,
            "total_processed": len(deletion_results),
            "successful_deletions": successful,
            "failed_deletions": failed,
            "results": deletion_results
        }

    @mcp.tool()
    async def cleanup_old_ranges(
        keep_user_ids: list[str],
        confirm: bool = False
    ) -> dict:
        """Delete all ranges EXCEPT those belonging to specified users.

        Useful for cleaning up test/temporary ranges while keeping production ones.

        Args:
            keep_user_ids: List of user IDs whose ranges should be KEPT (not deleted)
            confirm: Must be set to True to actually delete (safety measure)

        Returns:
            Deletion results

        Example:
            # Keep ranges for 'admin' and 'tjnull', delete all others
            result = await cleanup_old_ranges(
                keep_user_ids=["admin", "tjnull"],
                confirm=True
            )

        Safety:
            - Requires confirm=True to prevent accidental deletion
            - Shows preview of what will be deleted
            - Explicitly protects specified user ranges
        """
        handler = registry.get_handler("range", RangeHandler)

        # Get all ranges
        all_ranges = await handler.client.list_ranges()

        # Filter: delete everything NOT in keep list
        ranges_to_delete = [
            r for r in all_ranges
            if r.get("userID") not in keep_user_ids
        ]

        ranges_to_keep = [
            r for r in all_ranges
            if r.get("userID") in keep_user_ids
        ]

        if not confirm:
            # Preview mode
            return {
                "status": "preview",
                "message": f"[WARNING] DELETION PREVIEW - Set confirm=True to delete",
                "keep_user_ids": keep_user_ids,
                "ranges_to_keep": len(ranges_to_keep),
                "ranges_to_delete": len(ranges_to_delete),
                "kept_ranges": [
                    {
                        "user_id": r.get("userID"),
                        "range_number": r.get("rangeNumber"),
                        "status": r.get("rangeState"),
                    }
                    for r in ranges_to_keep
                ],
                "deleted_ranges": [
                    {
                        "user_id": r.get("userID"),
                        "range_number": r.get("rangeNumber"),
                        "status": r.get("rangeState"),
                        "vm_count": len(r.get("VMs", []))
                    }
                    for r in ranges_to_delete
                ],
                "warning": f"These {len(ranges_to_delete)} ranges will be PERMANENTLY DELETED if you set confirm=True",
                "next_step": f"To delete, call: cleanup_old_ranges(keep_user_ids={keep_user_ids}, confirm=True)"
            }

        # Actually delete non-kept ranges
        deletion_results = []
        for range_data in ranges_to_delete:
            user_id = range_data.get("userID")
            try:
                result = await handler.client.delete_range(user_id)
                deletion_results.append({
                    "user_id": user_id,
                    "status": "deleted",
                    "result": result
                })
            except Exception as e:
                deletion_results.append({
                    "user_id": user_id,
                    "status": "error",
                    "error": str(e)
                })

        successful = sum(1 for r in deletion_results if r["status"] == "deleted")
        failed = sum(1 for r in deletion_results if r["status"] == "error")

        return {
            "status": "completed",
            "message": f"[OK] Deleted {successful} ranges, kept {len(ranges_to_keep)} ranges",
            "kept_user_ids": keep_user_ids,
            "ranges_kept": len(ranges_to_keep),
            "ranges_deleted": successful,
            "ranges_failed": failed,
            "results": deletion_results
        }

    return mcp

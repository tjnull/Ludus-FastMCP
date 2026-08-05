"""Automation and orchestration FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.automation_orchestration import AutomationOrchestrationHandler
from ludus_mcp.server.handlers.backup import BackupHandler
from ludus_mcp.server.handlers.orchestration import DeploymentOrchestrator
from ludus_mcp.server.handlers.resource_management import ResourceManagementHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_automation_tools(client: LudusAPIClient) -> FastMCP:
    """Create automation and orchestration tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with automation tools registered
    """
    mcp = FastMCP("Automation & Orchestration")
    registry = LazyHandlerRegistry(client)

    # ==================== AUTOMATION TOOLS ====================

    @mcp.tool()
    async def create_deployment_pipeline(
        name: str,
        stages: list[dict[str, Any]],
        user_id: str | None = None
    ) -> dict:
        """Create a deployment pipeline with multiple stages.

        Args:
            name: Pipeline name
            stages: List of pipeline stages with configurations
            user_id: Optional user ID (admin only)

        Returns:
            Pipeline creation result
        """
        handler = registry.get_handler("automation", AutomationOrchestrationHandler)
        result = await handler.create_deployment_pipeline(
            pipeline_name=name, stages=stages, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def schedule_range_tasks(
        task_type: str,
        schedule: str,
        parameters: dict[str, Any] | None = None,
        user_id: str | None = None
    ) -> dict:
        """Schedule a recurring task for the range.

        Args:
            task_type: Type of task to schedule
            schedule: Cron expression for scheduling
            parameters: Optional task-specific parameters
            user_id: Optional user ID (admin only)

        Returns:
            Task scheduling result
        """
        handler = registry.get_handler("automation", AutomationOrchestrationHandler)
        result = await handler.schedule_range_tasks(
            task_type=task_type, schedule=schedule,
            parameters=parameters, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def auto_scaling(
        rules: list[dict[str, Any]],
        user_id: str | None = None
    ) -> dict:
        """Define auto-scaling rules based on resource usage.

        Args:
            rules: List of scaling rules, each describing the resource to watch,
                the threshold, and the action to take
            user_id: Optional user ID (admin only)

        Returns:
            Auto-scaling configuration result
        """
        handler = registry.get_handler("automation", AutomationOrchestrationHandler)
        result = await handler.auto_scaling(rules=rules, user_id=user_id)
        return format_tool_response(result)

    # ==================== SNAPSHOT AUTOMATION TOOLS ====================

    @mcp.tool()
    async def schedule_snapshots(
        vm_names: list[str],
        schedule: str,
        retention_count: int = 5,
        user_id: str | None = None
    ) -> dict:
        """Schedule automatic snapshots for VMs.

        Args:
            vm_names: List of VM names to snapshot
            schedule: Cron expression for snapshot schedule
            retention_count: Number of snapshots to retain
            user_id: Optional user ID (admin only)

        Returns:
            Snapshot scheduling result
        """
        handler = registry.get_handler("backup", BackupHandler)
        result = await handler.schedule_snapshots(vm_names, schedule, retention_count, user_id)
        return format_tool_response(result)

    # ==================== RANGE CLONING TOOLS ====================

    @mcp.tool()
    async def clone_range(
        target_user_id: str,
        include_snapshots: bool = False,
        user_id: str | None = None
    ) -> dict:
        """Clone the current range to another user.

        Args:
            target_user_id: User ID to clone range to
            include_snapshots: Whether to include snapshots in clone
            user_id: Optional user ID (admin only)

        Returns:
            Clone operation result
        """
        handler = registry.get_handler("backup", BackupHandler)
        result = await handler.clone_range(target_user_id, include_snapshots, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def export_range_backup(
        include_snapshots: bool = True,
        user_id: str | None = None
    ) -> dict:
        """Export a range backup (configuration and snapshot metadata).

        Args:
            include_snapshots: Include snapshot metadata in the backup
            user_id: Optional user ID (admin only)

        Returns:
            Backup export result
        """
        handler = registry.get_handler("backup", BackupHandler)
        result = await handler.export_range_backup(
            include_snapshots=include_snapshots, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def import_range_backup(
        backup_file: str,
        restore_vms: bool = True,
        restore_config: bool = True,
        user_id: str | None = None
    ) -> dict:
        """Import and restore range from backup.

        Args:
            backup_file: Path to backup file
            restore_vms: Restore VM disk images
            restore_config: Restore configuration
            user_id: Optional user ID (admin only)

        Returns:
            Backup import result
        """
        handler = registry.get_handler("backup", BackupHandler)
        result = await handler.import_range_backup(
            backup_file, restore_vms, restore_config, user_id
        )
        return format_tool_response(result)

    # ==================== BULK OPERATIONS ====================

    @mcp.tool()
    async def bulk_vm_operations(
        operation: str,
        vm_filter: dict[str, Any] | None = None,
        user_id: str | None = None
    ) -> dict:
        """Perform bulk operations on multiple VMs.

        Args:
            operation: Operation to perform (power_on, power_off, snapshot, delete, restart)
            vm_filter: Optional filter selecting which VMs to act on. Supported keys:
                "status" (exact match), "template" (substring), "name_pattern"
                (case-insensitive substring). Omit to target every VM in the range.
            user_id: Optional user ID (admin only)

        Returns:
            Bulk operation results
        """
        handler = registry.get_handler("resource_management", ResourceManagementHandler)
        result = await handler.bulk_vm_operations(
            operation=operation, vm_filter=vm_filter, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def delete_range(
        confirm: bool = False,
        user_id: str | None = None
    ) -> dict:
        """Delete the entire range.

        Permanently removes the range and all associated VMs, snapshots, and data.
        
        **Important:** If a deployment is in progress, abort it first with `abort_range_deployment()`.

        Args:
            confirm: Confirmation flag (must be True to proceed)
            user_id: Optional user ID (admin only)

        Returns:
            Range deletion result
            
        Example:
            # Delete current user's range (after aborting if needed)
            result = await delete_range(confirm=True)
            
        Workflow:
            1. If deployment is active: abort_range_deployment()
            2. Then delete: delete_range(confirm=True)
        """
        if not confirm:
            return {
                "error": "delete_range requires confirm=True to proceed",
                "warning": "This operation will permanently delete all VMs, snapshots, and data",
                "note": "If a deployment is in progress, abort it first with abort_range_deployment()",
                "safety": "This will ONLY delete the range for the specified user_id. Other users' ranges are protected."
            }
        # SAFETY: Always require explicit user_id or use current user
        # Pass require_explicit_user=False only when user_id is explicitly provided
        result = await client.delete_range(
            user_id=user_id,
            require_explicit_user=(user_id is not None)  # Only require explicit if user_id was provided
        )
        return format_tool_response(result)
    
    @mcp.tool()
    async def abort_and_remove_range(
        confirm: bool = False,
        user_id: str | None = None
    ) -> dict:
        """Abort any active deployment and then remove the range.
        
        This is a convenience function that combines abort_range_deployment() and delete_range().
        Equivalent to running:
        1. `ludus range abort`
        2. `ludus rm` (with confirmation)
        
        Args:
            confirm: Confirmation flag (must be True to proceed)
            user_id: Optional user ID (admin only)
            
        Returns:
            Combined abort and deletion results
            
        Example:
            # Abort and remove current user's range
            result = await abort_and_remove_range(confirm=True)
        """
        if not confirm:
            return {
                "error": "abort_and_remove_range requires confirm=True to proceed",
                "warning": "This will abort any active deployment and permanently delete the range",
                "workflow": "1. Abort deployment (if active) 2. Delete range"
            }
        
        results = {
            "abort_result": None,
            "delete_result": None,
            "status": "success"
        }
        
        # First, try to abort any active deployment
        try:
            abort_result = await client.abort_range_deployment(
                user_id=user_id,
                require_explicit_user=(user_id is not None)
            )
            results["abort_result"] = abort_result
            results["abort_status"] = "aborted" if abort_result else "no_active_deployment"
        except Exception as e:
            # If abort fails, it might mean there's no active deployment
            results["abort_result"] = {"note": f"No active deployment to abort or error: {str(e)}"}
            results["abort_status"] = "skipped"
        
        # Then delete the range with safety checks
        try:
            delete_result = await client.delete_range(
                user_id=user_id,
                require_explicit_user=(user_id is not None)  # Only require explicit if user_id was provided
            )
            results["delete_result"] = delete_result
            results["delete_status"] = "deleted"
        except Exception as e:
            results["delete_status"] = "failed"
            results["error"] = str(e)
            results["status"] = "partial_failure"
        
        return format_tool_response(results)

    @mcp.tool()
    async def get_recovery_recommendation(user_id: str | None = None) -> dict:
        """Get recovery recommendations for failed deployments.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Recovery recommendations based on failure analysis
        """
        handler = registry.get_handler("orchestrator", DeploymentOrchestrator)
        result = await handler.get_recovery_recommendation(user_id=user_id)
        return format_tool_response(result)

    return mcp

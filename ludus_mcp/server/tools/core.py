"""Core FastMCP tools for Ludus MCP server - ranges, hosts, snapshots, templates, power."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.ranges import RangeHandler
from ludus_mcp.server.handlers.power import PowerHandler
from ludus_mcp.server.handlers.snapshots import SnapshotHandler
from ludus_mcp.server.handlers.templates import TemplateHandler
from ludus_mcp.server.handlers.hosts import HostHandler
from ludus_mcp.server.handlers.networks import NetworkHandler
from ludus_mcp.server.handlers.testing import TestingHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_core_tools(client: LudusAPIClient) -> FastMCP:
    """Create core operation tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with core tools registered
    """
    mcp = FastMCP("Core Operations")
    registry = LazyHandlerRegistry(client)

    # ==================== RANGE TOOLS ====================

    @mcp.tool()
    async def get_range(user_id: str | None = None) -> dict:
        """Get current user's range information.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Range information
        """
        handler = registry.get_handler("range", RangeHandler)
        # The API method signature is different - it doesn't take user_id for get_range
        # We need to get the current user's range
        result = await handler.client.get_range(user_id)
        return result

    @mcp.tool()
    async def get_range_config(user_id: str | None = None) -> dict:
        """Get range configuration.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Range configuration
        """
        handler = registry.get_handler("range", RangeHandler)
        result = await handler.client.get_range_config(user_id)
        return result

    @mcp.tool()
    async def update_range_config(config: dict[str, Any], user_id: str | None = None) -> dict:
        """Update range configuration.

        Args:
            config: Range configuration object
            user_id: Optional user ID (admin only)

        Returns:
            Updated configuration
        """
        handler = registry.get_handler("range", RangeHandler)
        result = await handler.client.update_range_config(config, user_id)
        return result

    @mcp.tool()
    async def deploy_range(
        config: dict[str, Any] | None = None,
        user_id: str | None = None,
        tags: str | None = None,
        limit: str | None = None,
        only_roles: str | None = None,
        force: bool = False
    ) -> dict:
        """Deploy a range from configuration with optional filters for resuming.

        IMPORTANT: For deploying predefined scenarios (redteam-lab-lite, etc.),
        use deploy_scenario() or smart_deploy() instead. This tool is for:
        - Custom configurations you've built manually
        - Resuming partial deployments with tags/limit
        - Deploying after you've already set the config via update_range_config()

        This tool supports both full deployments and resuming partial deployments.

        **Full Deployment:**
            deploy_range(config=configuration_dict)

        **Resume After Pause/Abort:**
            deploy_range(tags="user,domain")  # Run specific Ansible tags only
            deploy_range(limit="DC*")         # Deploy only to matching VMs
            deploy_range(tags="user", limit="WS*")  # Combine filters

        **Common Ansible Tags:**
            - "base": Base system configuration
            - "domain": Domain join operations
            - "user": User creation and management
            - "configure": General configuration
            - "testing": Testing configuration
            Use get_range_tags() to see all available tags for your range

        Args:
            config: Range configuration (required for full deployment, optional for resume)
            user_id: Optional user ID (admin only)
            tags: Ansible tags to run (comma-separated, e.g., "user,domain")
            limit: Limit to VMs matching pattern (e.g., "DC*", "WS*", "*-DC01")
            only_roles: Limit user-defined roles (comma-separated)
            force: Force deployment if testing is enabled

        Returns:
            Deployment result

        **Use Cases:**
            1. Initial deployment: `deploy_range(config=my_config)`
            2. Resume after abort: `deploy_range(tags="user,domain")`
            3. Re-run specific tags: `deploy_range(tags="configure")`
            4. Fix specific VM: `deploy_range(limit="DC01")`
            5. Update workstations only: `deploy_range(limit="WS*", tags="user")`
            6. After role installation: `deploy_range(tags="configure")`

        **Example Workflow - Resume After Failure:**
            1. abort_range_deployment()  # Stop the failed deployment
            2. get_range_tags()          # See available tags
            3. deploy_range(tags="user,domain")  # Resume from specific step
        """
        handler = registry.get_handler("range", RangeHandler)
        
        # IMPORTANT: If a config is provided, we must set it first via PUT /range/config
        # The Ludus API requires the config to be stored before deployment
        # This matches the CLI workflow: "ludus range config set -f config.yml && ludus range deploy"
        if config is not None:
            import asyncio
            from ludus_mcp.utils.logging import get_logger
            logger = get_logger(__name__)
            
            # Set the configuration first
            expected_vms = config.get('ludus', [])
            expected_vm_count = len(expected_vms) if isinstance(expected_vms, list) else 0
            logger.info(f"Setting range configuration with {expected_vm_count} VMs")
            
            try:
                await handler.client.update_range_config(config, user_id)
                logger.info(f"✓ update_range_config API call completed")
                
                # CRITICAL: Verify the configuration was actually set
                logger.info(f"Verifying configuration was set correctly...")
                await asyncio.sleep(2.0)  # Longer delay to ensure config is persisted (file upload processing)
                
                stored_config = await handler.client.get_range_config(user_id)
                logger.info(f"Retrieved stored config - keys: {list(stored_config.keys()) if isinstance(stored_config, dict) else 'not a dict'}")
                
                # Handle different config formats that Ludus might return
                stored_vms = stored_config.get('ludus', [])
                
                # Also check if config is nested differently
                if not stored_vms and isinstance(stored_config, dict):
                    # Try alternative locations
                    if 'config' in stored_config:
                        stored_vms = stored_config['config'].get('ludus', [])
                    elif 'range_config' in stored_config:
                        stored_vms = stored_config['range_config'].get('ludus', [])
                
                if not isinstance(stored_vms, list):
                    stored_vms = []
                
                stored_vm_count = len(stored_vms) if isinstance(stored_vms, list) else 0
                
                logger.info(f"Stored config has {stored_vm_count} VMs (expected {expected_vm_count})")
                
                if stored_vm_count != expected_vm_count:
                    error_msg = (
                        f"CONFIGURATION VERIFICATION FAILED: "
                        f"Expected {expected_vm_count} VMs but stored config has {stored_vm_count} VMs. "
                        f"The configuration was not properly set in Ludus. "
                        f"Aborting deployment to prevent using incorrect configuration."
                    )
                    logger.error(error_msg)
                    return {
                        "status": "error",
                        "error": error_msg,
                        "expected_vm_count": expected_vm_count,
                        "stored_vm_count": stored_vm_count,
                    }
                
                # Verify key VMs are present
                if expected_vm_count > 0:
                    expected_vm_names = {vm.get('vm_name') for vm in expected_vms if vm.get('vm_name')}
                    stored_vm_names = {vm.get('vm_name') for vm in stored_vms if isinstance(stored_vms, list) and vm.get('vm_name')}
                    
                    if expected_vm_names and not expected_vm_names.issubset(stored_vm_names):
                        missing = expected_vm_names - stored_vm_names
                        error_msg = (
                            f"CONFIGURATION VERIFICATION FAILED: "
                            f"Expected VMs missing from stored config: {missing}. "
                            f"The configuration was not properly set in Ludus."
                        )
                        logger.error(error_msg)
                        return {
                            "status": "error",
                            "error": error_msg,
                            "missing_vms": list(missing),
                        }
                
                logger.info(f"✓ Configuration verified: {stored_vm_count} VMs correctly stored")
                
            except Exception as e:
                error_msg = f"Failed to set or verify range configuration: {e}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "error": error_msg,
                }
            
            # Now deploy using the stored configuration (pass None to use stored config)
            result = await handler.client.deploy_range(
                config=None,
                user_id=user_id,
                tags=tags,
                limit=limit,
                only_roles=only_roles,
                force=force
            )
        else:
            # No config provided - deploying with existing stored configuration or resuming
            result = await handler.client.deploy_range(
                config=None,
                user_id=user_id,
                tags=tags,
                limit=limit,
                only_roles=only_roles,
                force=force
            )
        return result

    @mcp.tool()
    async def get_range_tags(user_id: str | None = None) -> list[str]:
        """Get available Ansible tags for the current range.

        Use this to see what tags are available for resuming/partial deployments.
        Tags allow you to run specific parts of a deployment without re-running everything.

        Common tags include:
            - base: Base system setup
            - domain: Domain join and AD operations
            - user: User and group creation
            - configure: Configuration tasks
            - testing: Testing-related tasks
            - vm-customize: VM customization
            - sysprep: Windows sysprep operations

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            List of available Ansible tags

        Example:
            tags = await get_range_tags()
            # Returns: ["base", "domain", "user", "configure", ...]

            # Use tags to resume deployment
            deploy_range(tags="user,domain")
        """
        handler = registry.get_handler("range", RangeHandler)
        result = await handler.client.get_range_tags()
        return result

    @mcp.tool()
    async def abort_range_deployment(user_id: str | None = None) -> dict:
        """Abort a range deployment.

        Stops an active deployment. Use this before deleting a range that is currently deploying.
        After aborting, you can resume the deployment using deploy_range() with specific tags.

        Equivalent to: `ludus range abort`

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Abort result

        Example Workflow - Abort and Resume:
            # 1. Abort the deployment
            result = await abort_range_deployment()

            # 2. Check what tags are available
            tags = await get_range_tags()

            # 3. Resume from where it stopped
            deploy_range(tags="user,domain")

        Note:
            After aborting, you can also:
            - Delete the range: delete_range(confirm=True)
            - Abort and delete: abort_and_remove_range(confirm=True)
            - Resume deployment: deploy_range(tags="...")
        """
        handler = registry.get_handler("range", RangeHandler)
        result = await handler.client.abort_range_deployment(user_id)
        return result

    # ==================== SNAPSHOT TOOLS ====================

    @mcp.tool()
    async def snapshot_host(
        vm_name: str,
        name: str,
        description: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Create a snapshot of a host.

        Args:
            vm_name: Name of the VM to snapshot
            name: Name of the snapshot
            description: Optional snapshot description
            user_id: Optional user ID (admin only)

        Returns:
            Snapshot creation result
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)
        snapshot_config = {"vm_name": vm_name, "name": name, "description": description}
        result = await handler.create_snapshot(snapshot_config, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def list_snapshots(user_id: str | None = None) -> list[dict]:
        """List all snapshots for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            List of snapshots
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)
        result = await handler.list_snapshots(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def rollback_snapshot(
        vm_name: str,
        snapshot_name: str,
        user_id: str | None = None
    ) -> dict:
        """Rollback to a snapshot.

        Args:
            vm_name: Name of the VM
            snapshot_name: Name of the snapshot to rollback to
            user_id: Optional user ID (admin only)

        Returns:
            Rollback result
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)
        result = await handler.rollback_snapshot({"vm_name": vm_name, "name": snapshot_name}, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def remove_snapshot(
        vm_name: str,
        snapshot_name: str,
        user_id: str | None = None
    ) -> dict:
        """Remove a snapshot.

        Args:
            vm_name: Name of the VM
            snapshot_name: Name of the snapshot to remove
            user_id: Optional user ID (admin only)

        Returns:
            Removal result
        """
        handler = registry.get_handler("snapshot", SnapshotHandler)
        result = await handler.remove_snapshot({"vm_name": vm_name, "name": snapshot_name}, user_id)
        return format_tool_response(result)

    # ==================== POWER TOOLS ====================

    @mcp.tool()
    async def power_on_range(user_id: str | None = None) -> dict:
        """Power on all VMs in the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Power on result
        """
        handler = registry.get_handler("power", PowerHandler)
        result = await handler.power_on_range(user_id)
        return result

    @mcp.tool()
    async def power_off_range(user_id: str | None = None) -> dict:
        """Power off all VMs in the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Power off result
        """
        handler = registry.get_handler("power", PowerHandler)
        result = await handler.power_off_range(user_id)
        return result

    # ==================== TEMPLATE TOOLS ====================

    @mcp.tool()
    async def list_templates(user_id: str | None = None) -> list[dict]:
        """List available templates.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            List of available templates
        """
        handler = registry.get_handler("template", TemplateHandler)
        result = await handler.list_templates(user_id)
        return format_tool_response(result)

    # ==================== HOST TOOLS ====================

    @mcp.tool()
    async def list_hosts(user_id: str | None = None) -> list[dict]:
        """List all hosts in range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            List of hosts
        """
        handler = registry.get_handler("range", RangeHandler)
        # Get range first to extract hosts
        range_info = await handler.client.get_range(user_id)
        vms = range_info.get("VMs", [])
        return vms

    # ==================== NETWORK TOOLS ====================

    @mcp.tool()
    async def list_networks(user_id: str | None = None) -> list[dict]:
        """List all networks in a range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            List of networks
        """
        handler = registry.get_handler("range", RangeHandler)
        # Get range first to extract networks
        range_info = await handler.client.get_range(user_id)
        networks = range_info.get("networks", [])
        return networks

    # ==================== TESTING TOOLS ====================

    @mcp.tool()
    async def start_testing(user_id: str | None = None) -> dict:
        """Start testing state for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Testing start result
        """
        handler = registry.get_handler("testing", TestingHandler)
        result = await handler.start_testing(user_id)
        return result

    @mcp.tool()
    async def stop_testing(user_id: str | None = None) -> dict:
        """Stop testing state for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Testing stop result
        """
        handler = registry.get_handler("testing", TestingHandler)
        result = await handler.stop_testing(user_id)
        return result

    # ==================== HEALTH CHECK TOOL ====================

    @mcp.tool()
    async def health_check() -> dict:
        """Check health of Ludus MCP server and Ludus API connectivity.

        Uses the ludus CLI if available for more reliable connectivity testing.

        Returns:
            Health status including:
            - Server status (healthy/unhealthy)
            - MCP version
            - Ludus API reachability
            - Connection latency
            - Number of available tools
            - Configuration sources
            - Ludus server version (if connected)
        """
        import time
        import shutil
        import subprocess
        import os
        from pathlib import Path
        from importlib.metadata import version
        from ludus_mcp.utils.config import get_settings

        start_time = time.time()
        try:
            actual_version = version("ludus-fastmcp")
        except Exception:
            actual_version = "1.0.0"  # Fallback version

        # Get current settings for debug info
        settings = get_settings()

        # Check which .env files exist
        env_files_found = []
        home_env = Path.home() / ".ludus-fastmcp" / ".env"
        cwd_env = Path.cwd() / ".env"
        if home_env.exists():
            env_files_found.append(str(home_env))
        if cwd_env.exists():
            env_files_found.append(str(cwd_env))

        health_info = {
            "status": "unknown",
            "mcp_version": actual_version,
            "tools_available": 157,
            "timestamp": time.time(),
            "config": {
                "api_url": settings.ludus_api_url,
                "api_key_set": bool(settings.ludus_api_key),
                "api_key_preview": f"{'*' * 10}...{settings.ludus_api_key[-8:]}" if settings.ludus_api_key else "NOT SET",
                "ssl_verify": settings.ludus_ssl_verify,
                "env_files_found": env_files_found,
                "cwd": str(Path.cwd()),
            },
        }

        # Prefer ludus CLI for health check if available
        ludus_cli = shutil.which("ludus")
        if ludus_cli and settings.ludus_api_key:
            try:
                env = os.environ.copy()
                env["LUDUS_API_KEY"] = settings.ludus_api_key

                # Use 'ludus version' - lightweight command that verifies connectivity
                result = subprocess.run(
                    ["ludus", "version", "--url", settings.ludus_api_url],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env=env
                )

                latency_ms = round((time.time() - start_time) * 1000, 2)

                if result.returncode == 0:
                    output = (result.stdout + result.stderr).strip()
                    # Parse versions from output
                    # Example: "[INFO]  Ludus client 1.11.5+b9fe95c"
                    #          "[INFO]  Ludus Server 1.11.4+b1da5c6 - community license"
                    server_version = None
                    client_version = None
                    license_type = None
                    for line in output.split('\n'):
                        if 'Ludus Server' in line:
                            parts = line.split('Ludus Server')[-1].strip()
                            server_version = parts.split()[0] if parts else None
                            if ' - ' in parts:
                                license_type = parts.split(' - ')[-1].strip()
                        elif 'Ludus client' in line:
                            client_version = line.split('Ludus client')[-1].strip()

                    health_info.update({
                        "status": "healthy",
                        "ludus_api": {
                            "reachable": True,
                            "latency_ms": latency_ms,
                            "base_url": settings.ludus_api_url,
                            "server_version": server_version,
                            "client_version": client_version,
                            "license": license_type,
                            "method": "ludus_cli",
                        },
                    })
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    health_info.update({
                        "status": "unhealthy",
                        "error": error_msg[:200],
                        "ludus_api": {
                            "reachable": False,
                            "base_url": settings.ludus_api_url,
                            "method": "ludus_cli",
                        },
                    })
            except subprocess.TimeoutExpired:
                health_info.update({
                    "status": "unhealthy",
                    "error": "Connection timed out",
                    "ludus_api": {"reachable": False, "base_url": settings.ludus_api_url},
                })
            except Exception as e:
                health_info.update({
                    "status": "unhealthy",
                    "error": f"CLI error: {str(e)}",
                    "error_type": type(e).__name__,
                })
        else:
            # Fallback to httpx client
            try:
                from ludus_mcp.exceptions import LudusConnectionError, LudusTimeoutError

                await client.get_host_info()
                latency_ms = round((time.time() - start_time) * 1000, 2)

                rate_stats = {}
                if hasattr(client, "rate_limiter"):
                    rate_stats = client.rate_limiter.get_current_usage()

                health_info.update({
                    "status": "healthy",
                    "ludus_api": {
                        "reachable": True,
                        "latency_ms": latency_ms,
                        "base_url": client.base_url,
                        "method": "httpx_client",
                    },
                    "rate_limiter": rate_stats,
                })

            except (LudusConnectionError, LudusTimeoutError) as e:
                health_info.update({
                    "status": "unhealthy",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "ludus_api": {
                        "reachable": False,
                        "base_url": client.base_url,
                    },
                })

            except Exception as e:
                health_info.update({
                    "status": "unhealthy",
                    "error": f"Unexpected error: {str(e)}",
                    "error_type": type(e).__name__,
                })

        return health_info

    return mcp

# Import deployment tools into core
from ludus_mcp.server.handlers.scenarios import ScenarioHandler
from ludus_mcp.server.handlers.deployment import DeploymentHandler
from ludus_mcp.server.handlers.orchestration import DeploymentOrchestrator
from ludus_mcp.server.handlers.validation import ValidationHandler

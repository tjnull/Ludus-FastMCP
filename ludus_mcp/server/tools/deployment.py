"""Deployment FastMCP tools - scenarios, orchestration, monitoring."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.scenarios import ScenarioHandler
from ludus_mcp.server.handlers.deployment import DeploymentHandler
from ludus_mcp.server.handlers.orchestration import DeploymentOrchestrator
from ludus_mcp.server.handlers.validation import ValidationHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_deployment_tools(client: LudusAPIClient) -> FastMCP:
    """Create deployment operation tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with deployment tools registered
    """
    mcp = FastMCP("Deployment Operations")
    registry = LazyHandlerRegistry(client)

    # ==================== SCENARIO TOOLS ====================

    @mcp.tool()
    async def list_scenarios() -> dict[str, str]:
        """List all available scenarios.

        Returns:
            Dictionary of scenario keys and descriptions
        """
        handler = registry.get_handler("scenario", ScenarioHandler)
        result = await handler.list_scenarios()
        return result

    @mcp.tool()
    async def deploy_scenario(
        scenario_key: str,
        user_id: str | None = None,
        ensure_roles: bool = True,
        siem_type: str = "wazuh",
        resource_profile: str = "recommended",
        customize: bool = False,
        randomize: bool = False,
        custom_users: list[dict[str, Any]] | None = None,
        vulnerability_config: dict[str, Any] | None = None,
        network_customizations: dict[str, Any] | None = None,
        vm_customizations: dict[str, Any] | None = None,
    ) -> dict:
        """Deploy a scenario with optional SIEM integration and customization.

        IMPORTANT: This tool generates a FRESH configuration for each call.
        Each deployment builds a new scenario from scratch - no state is reused.
        
        NO FILE UPLOAD REQUIRED: This tool automatically generates the configuration
        from the scenario parameters. You do NOT need to provide a config file or
        manual configuration.

        CUSTOMIZATION AND RANDOMIZATION:
        - Use customize=True with custom parameters to deploy a customized scenario
        - Use randomize=True to deploy a randomized version with varied users/vulnerabilities
        - All customization parameters are optional - defaults used if not specified

        Recommended Workflow:
        1. Use preview_scenario() first to verify what will be deployed
        2. (Optional) Abort any existing deployment: abort_range_deployment()
        3. (Optional) Delete existing range: delete_range(confirm=True)
        4. Deploy the scenario: deploy_scenario(scenario_key='redteam-lab-lite')
        5. Monitor progress: monitor_deployment() or quick_status()

        Internal Workflow:
        1. Generates fresh scenario configuration based on parameters
        2. Applies customizations or randomization if requested
        3. Sets the configuration in Ludus (via PUT /range/config)
        4. Verifies the configuration was set correctly
        5. Starts deployment (via POST /range/deploy)
        6. Generates comprehensive walkthrough
        7. Returns deployment status, VM details, and walkthrough

        Available scenarios:
        - redteam-lab-lite: 5 VMs (DC, 2 workstations, file server, Kali)
        - redteam-lab-intermediate: 10 VMs (DMZ, internal network, multiple servers)
        - redteam-lab-advanced: 21 VMs (2 forests with trust, DMZ, secure zone)
        - blueteam-lab-lite: 6 VMs (SOC with SIEM, detection)
        - blueteam-lab-intermediate: 11 VMs (SOC with EDR, IDS)
        - blueteam-lab-advanced: 21 VMs (Enterprise SOC, full stack)
        - purpleteam-lab-lite: 6 VMs (Red/Blue collaborative)
        - purpleteam-lab-intermediate: 10 VMs (Purple team with EDR)
        - purpleteam-lab-advanced: 13 VMs (Full SOC + adversary emulation)
        - malware-re-lab-lite: 3 VMs (Basic malware analysis)
        - malware-re-lab-intermediate: 7 VMs (Pro malware lab)
        - malware-re-lab-advanced: 18 VMs (Enterprise malware research)
        - wireless-lab: 2 VMs (WiFi pentesting)

        Args:
            scenario_key: Scenario identifier (e.g., 'redteam-lab-lite')
            user_id: Optional user ID (admin only)
            ensure_roles: Ensure required Ansible roles are installed
            siem_type: SIEM type to include (wazuh, splunk, elastic, security-onion, none)
            resource_profile: Resource allocation profile (minimal, recommended, maximum)
            customize: Enable customization mode (use provided customizations)
            randomize: Enable randomization mode (generate random customizations)
            custom_users: List of custom user dicts with keys: username, password, display_name, 
                         groups (list), department (optional), title (optional), etc.
            vulnerability_config: Dict with keys like esc1_enabled, esc2_enabled, open_shares, etc.
            network_customizations: Dict with vlan_changes, additional_rules, remove_rules, etc.
            vm_customizations: Dict with vm_count_overrides, additional_vms, remove_vms, etc.

        Returns:
            Deployment result with scenario details, VM list, deployment status, and walkthrough

        Examples:
            # Simple deployment (default)
            deploy_scenario(scenario_key='redteam-lab-lite', siem_type='none')
            
            # Randomized deployment
            deploy_scenario(scenario_key='redteam-lab-lite', randomize=True)
            
            # Custom users deployment
            deploy_scenario(
                scenario_key='redteam-lab-lite',
                customize=True,
                custom_users=[
                    {
                        "username": "admin.user",
                        "password": "CustomPass123!",
                        "display_name": "Admin User",
                        "groups": ["Domain Users", "Domain Admins"],
                        "department": "IT"
                    }
                ]
            )
            
            # Custom vulnerabilities
            deploy_scenario(
                scenario_key='redteam-lab-lite',
                customize=True,
                vulnerability_config={
                    "esc1_enabled": True,
                    "esc8_enabled": True,
                    "open_shares": True
                }
            )
            
        Natural Language Translation:
        - "Make a custom range using redteam-lab-lite" → customize=True
        - "Randomize redteam-lab-lite" → randomize=True
        - "Deploy with different users" → customize=True, custom_users=[...]
            
        Note: For automated deployments with validation and monitoring,
        consider using smart_deploy() instead, which handles the full workflow.
        """
        handler = registry.get_handler("scenario", ScenarioHandler)
        result = await handler.deploy_scenario(scenario_key, user_id, ensure_roles, siem_type, resource_profile)
        return result

    @mcp.tool()
    async def get_scenario_config(
        scenario_key: str,
        siem_type: str = "wazuh"
    ) -> dict:
        """Get scenario configuration.

        Args:
            scenario_key: Scenario identifier
            siem_type: SIEM type to include

        Returns:
            Scenario configuration
        """
        handler = registry.get_handler("scenario", ScenarioHandler)
        result = await handler.get_scenario_config(scenario_key, siem_type)
        return result

    @mcp.tool()
    async def get_scenario_yaml(
        scenario_key: str,
        siem_type: str = "wazuh"
    ) -> str:
        """Get scenario configuration as YAML.

        Args:
            scenario_key: Scenario identifier
            siem_type: SIEM type to include

        Returns:
            YAML configuration string
        """
        handler = registry.get_handler("scenario", ScenarioHandler)
        result = await handler.get_scenario_yaml(scenario_key, siem_type)
        return result

    @mcp.tool()
    async def preview_scenario(
        scenario_key: str,
        siem_type: str = "wazuh",
        resource_profile: str = "recommended"
    ) -> dict:
        """Preview a scenario before deployment with detailed information.

        IMPORTANT: Generates a FRESH configuration preview for the specified scenario.
        Use this BEFORE deploy_scenario to verify what will be deployed.

        Shows VMs, network topology, resource requirements, and deployment estimates.
        Each preview call builds the scenario from scratch with your specified parameters.

        Args:
            scenario_key: Scenario identifier (e.g., 'redteam-lab-lite')
            siem_type: SIEM type to include (wazuh, splunk, elastic, security-onion, none)
            resource_profile: Resource allocation profile (minimal, recommended, maximum)

        Returns:
            Preview with configuration, visualization, and estimates including:
            - Complete VM list with hostnames, templates, resources
            - Network rules and VLAN topology
            - Resource summary (total RAM, CPUs, disk space)
            - Estimated deployment time
            - Exact deployment command to use

        Recommended workflow:
            1. preview_scenario('redteam-lab-lite', 'none', 'minimal')
            2. Review the VM list and resources
            3. deploy_scenario('redteam-lab-lite', 'none', 'minimal')
        """
        handler = registry.get_handler("scenario", ScenarioHandler)
        result = await handler.preview_scenario(scenario_key, siem_type, resource_profile)
        return format_tool_response(result)

    # ==================== DEPLOYMENT STATUS TOOLS ====================

    @mcp.tool()
    async def quick_status(user_id: str | None = None) -> str:
        """Get one-line deployment status with emoji indicators.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Formatted status string
        """
        handler = registry.get_handler("deployment", DeploymentHandler)
        result = await handler.quick_status(user_id)
        return result

    @mcp.tool()
    async def get_deployment_status(user_id: str | None = None) -> dict:
        """Get current deployment status with detailed information.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Detailed deployment status
        """
        handler = registry.get_handler("deployment", DeploymentHandler)
        result = await handler.get_deployment_status(user_id)
        return result

    @mcp.tool()
    async def get_range_logs(
        tail: int | None = 200,
        user_id: str | None = None
    ) -> str:
        """Get deployment logs for the range.

        Deployment logs run to tens of thousands of lines, so this returns the
        last 200 by default. Pass tail=None for the whole log.

        Args:
            tail: Return only the last N lines (default 200)
            user_id: Optional user ID (admin only)

        Returns:
            Deployment logs
        """
        result = await client.get_range_logs(user_id=user_id, tail=tail)
        return result

    # ==================== ORCHESTRATION TOOLS ====================

    @mcp.tool()
    async def smart_deploy(
        scenario_key: str,
        siem_type: str = "wazuh",
        auto_validate: bool = True,
        auto_snapshot: bool = False,
        auto_monitor: bool = True,
        user_id: str | None = None
    ) -> dict:
        """Smart deployment with validation, optional snapshot, and auto-monitoring.
        
        RECOMMENDED: This is the preferred method for deploying scenarios as it includes
        validation, error checking, and monitoring guidance.
        
        NO FILE UPLOAD REQUIRED: This tool automatically generates the configuration
        from the scenario parameters. You do NOT need to provide a config file.

        Workflow:
        1. Validates the scenario configuration (if auto_validate=True)
        2. Creates snapshot if requested (if auto_snapshot=True)
        3. Generates and sets the configuration in Ludus
        4. Verifies the configuration was set correctly
        5. Starts the deployment
        6. Provides monitoring guidance and commands

        When to use:
        - Use smart_deploy() for most deployments (recommended)
        - Use deploy_scenario() if you need more control or don't want validation
        - Use deploy_range() only if you have a custom configuration dict

        Args:
            scenario_key: Scenario to deploy (e.g., 'redteam-lab-lite')
            siem_type: SIEM type to include (wazuh, splunk, elastic, security-onion, none)
            auto_validate: Validate configuration before deploying (default: True)
            auto_snapshot: Create snapshot before deployment (default: False)
            auto_monitor: Enable auto-monitoring after deployment (default: True)
            user_id: Optional user ID (admin only)

        Returns:
            Smart deployment result with monitoring guidance and status

        Example:
            # Recommended: Use smart_deploy for automated deployments
            smart_deploy(
                scenario_key='redteam-lab-lite',
                siem_type='none',
                auto_validate=True,
                auto_monitor=True
            )
        """
        handler = registry.get_handler("orchestrator", DeploymentOrchestrator)
        result = await handler.smart_deploy(
            scenario_key, siem_type, auto_validate, auto_snapshot, auto_monitor, user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def monitor_deployment(
        user_id: str | None = None,
        check_interval: int = 30,
        max_checks: int = 40
    ) -> dict:
        """Monitor deployment progress with periodic updates.

        Args:
            user_id: Optional user ID (admin only)
            check_interval: Seconds between checks
            max_checks: Maximum number of checks

        Returns:
            Monitoring update with progress information
        """
        handler = registry.get_handler("orchestrator", DeploymentOrchestrator)
        result = await handler.monitor_deployment_once(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def deployment_timeline(user_id: str | None = None) -> dict:
        """Get deployment timeline with progress tracking.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Timeline with steps and progress
        """
        handler = registry.get_handler("deployment", DeploymentHandler)
        result = await handler.get_deployment_timeline(user_id=user_id)
        return format_tool_response(result)

    # ==================== VALIDATION TOOLS ====================

    @mcp.tool()
    async def validate_config(config: dict[str, Any]) -> dict:
        """Validate range configuration before deployment.

        Args:
            config: Range configuration to validate

        Returns:
            Validation result with errors and warnings
        """
        handler = registry.get_handler("validation", ValidationHandler)
        result = await handler.validate_config(config)
        return format_tool_response(result)

    @mcp.tool()
    async def handle_adws_recovery(
        wait_minutes: int = 10,
        auto_retry: bool = True,
        user_id: str | None = None,
    ) -> dict:
        """Handle Active Directory Web Services (ADWS) recovery for stuck deployments.

        ADWS errors are common during Active Directory deployments. This tool:
        1. Checks if deployment is stuck on ADWS errors
        2. Waits for ADWS to start (default: 10 minutes)
        3. Optionally retries the failed tasks automatically

        **When to use:**
        - Deployment failed with "Unable to find a default server with Active Directory Web Services running"
        - Deployment is stuck on OU configuration tasks
        - DC VM is deployed but AD services haven't fully started

        **What this does:**
        - Checks deployment logs for ADWS errors
        - Waits for ADWS to initialize (5-15 minutes typical)
        - Retries failed Ansible tasks (if auto_retry=True)
        - Provides status updates during wait

        Args:
            wait_minutes: Minutes to wait for ADWS to start (default: 10, max: 30)
            auto_retry: Automatically retry failed tasks after wait (default: True)
            user_id: Optional user ID (admin only)

        Returns:
            Recovery result with status and next steps

        Example:
            # Handle ADWS recovery with auto-retry
            result = await handle_adws_recovery(wait_minutes=10, auto_retry=True)
            
            # Just wait and check status (manual retry later)
            result = await handle_adws_recovery(wait_minutes=15, auto_retry=False)
        """
        import asyncio
        handler = registry.get_handler("deployment", DeploymentHandler)
        
        try:
            # Check current deployment status
            range_info = await handler.client.get_range(user_id)
            range_state = range_info.get("rangeState", "UNKNOWN")
            
            # Get logs to check for ADWS errors
            logs = await handler.get_full_logs(user_id)
            logs_text = logs.get("logs", "") if isinstance(logs, dict) else str(logs)
            logs_lower = logs_text.lower()
            
            has_adws_error = (
                "active directory web services" in logs_lower or
                "adws" in logs_lower or
                "unable to find a default server with active directory web services" in logs_lower
            )
            
            if not has_adws_error and range_state not in ["DEPLOYING", "CONFIGURING"]:
                return format_tool_response({
                    "status": "no_action_needed",
                    "message": "No ADWS errors detected. Deployment may have completed or failed for other reasons.",
                    "range_state": range_state,
                    "suggestion": "Check deployment status: quick_status() or get_deployment_status()",
                })
            
            result = {
                "status": "recovery_started",
                "adws_error_detected": has_adws_error,
                "range_state": range_state,
                "wait_minutes": min(wait_minutes, 30),  # Cap at 30 minutes
                "auto_retry": auto_retry,
                "steps": [],
            }
            
            # Wait for ADWS to start
            wait_seconds = min(wait_minutes, 30) * 60
            check_interval = 60  # Check every minute
            checks = wait_seconds // check_interval
            
            result["steps"].append(f"Waiting {wait_minutes} minutes for ADWS to start...")
            result["steps"].append("ADWS typically starts 5-15 minutes after domain promotion")
            result["steps"].append(f"Checking deployment status every {check_interval} seconds")
            
            # Wait and check periodically
            for i in range(checks):
                await asyncio.sleep(check_interval)
                
                # Check if deployment completed
                current_info = await handler.client.get_range(user_id)
                current_state = current_info.get("rangeState", "UNKNOWN")
                
                if current_state == "READY":
                    result["status"] = "recovery_success"
                    result["message"] = "Deployment completed successfully during wait period!"
                    result["steps"].append(f"✓ Deployment completed after {i+1} minutes")
                    return format_tool_response(result)
                
                # Check if ADWS errors are gone
                current_logs = await handler.get_full_logs(user_id)
                current_logs_text = current_logs.get("logs", "") if isinstance(current_logs, dict) else str(current_logs)
                if "active directory web services" not in current_logs_text.lower():
                    result["status"] = "adws_started"
                    result["steps"].append(f"✓ ADWS appears to have started after {i+1} minutes")
                    break
            
            # If auto_retry is enabled, retry failed tasks
            if auto_retry and result["status"] == "adws_started":
                result["steps"].append("Attempting to retry failed tasks...")
                try:
                    # Retry deployment with configure tags (OU creation, user creation, etc.)
                    retry_result = await handler.client.deploy_range(
                        config=None,
                        user_id=user_id,
                        tags="configure,user",  # Common tags for AD configuration
                    )
                    result["status"] = "retry_initiated"
                    result["retry_result"] = retry_result
                    result["steps"].append("✓ Retry initiated - deployment should continue")
                except Exception as e:
                    result["status"] = "retry_failed"
                    result["error"] = str(e)
                    result["steps"].append(f"✗ Retry failed: {e}")
                    result["steps"].append("You may need to manually retry: deploy_range(tags='configure,user')")
            
            if result["status"] == "recovery_started":
                result["status"] = "wait_complete"
                result["message"] = f"Wait period completed. Check deployment status and retry if needed."
                result["steps"].append("If ADWS still not started, wait longer or check DC VM status")
            
            result["next_steps"] = [
                "Check deployment status: quick_status()",
                "If still failing, wait longer: handle_adws_recovery(wait_minutes=15)",
                "Or manually retry: deploy_range(tags='configure,user')",
                "Check DC VM is running: get_range()",
            ]
            
            return format_tool_response(result)
            
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "error": str(e),
                "message": "Failed to handle ADWS recovery",
            })

    return mcp

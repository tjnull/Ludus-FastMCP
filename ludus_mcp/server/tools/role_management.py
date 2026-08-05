"""MCP tools for managing Ansible role installation."""

import os
from typing import Any

from fastmcp import FastMCP

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.scenarios.role_manager import RoleManager
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response

logger = None


async def _scenario_config(client, scenario_key: str, siem_type: str) -> dict | None:
    """Build a scenario's config so its roles can be read from it directly.

    Returns None if it cannot be built - callers then fall back to inferring
    roles from the scenario key.
    """
    try:
        from ludus_mcp.scenarios.scenario_manager import ScenarioManager

        result = await ScenarioManager(client).get_scenario_config(
            scenario_key, siem_type=siem_type
        )
        return result.get("config", result) if isinstance(result, dict) else None
    except Exception:  # pragma: no cover - best effort only
        return None


def create_role_management_tools(client: LudusAPIClient) -> FastMCP:
    """Create MCP tools for managing Ansible role installation."""
    global logger
    from ludus_mcp.utils.logging import get_logger
    logger = get_logger(__name__)

    mcp = FastMCP("Role Management")

    registry = LazyHandlerRegistry(client)

    @mcp.tool()
    async def list_installed_roles() -> dict:
        """List all installed Ansible roles on the Ludus server.

        Uses the ludus CLI with --url when available for reliable remote access.
        Falls back to HTTP API if CLI is not available.

        Returns:
            Dictionary with list of installed roles and their details

        Example:
            result = await list_installed_roles()
            # Returns: {"installed_roles": [...], "count": 15}
        """
        # Initialize RoleManager (no SSH needed for listing)
        role_manager = RoleManager(client)
        try:
            # Use the new get_installed_roles method which prefers CLI
            roles = await role_manager.get_installed_roles()

            return format_tool_response({
                "status": "success",
                "installed_roles": roles,
                "count": len(roles),
            })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "error": str(e),
            })

    @mcp.tool()
    async def check_role_installed(role_name: str) -> dict:
        """Check if a specific Ansible role is installed.

        Uses the ludus CLI with --url when available for reliable remote access.
        Falls back to HTTP API if CLI is not available. No SSH required.

        Args:
            role_name: Name of the role to check (e.g., "ludus-ad-content", "badsectorlabs.ludus_adcs")

        Returns:
            Dictionary indicating if the role is installed

        Example:
            # Check if a role is installed
            result = await check_role_installed(role_name="ludus-ad-content")

            # If not installed, use install_role() to install it
            if not result.get("installed"):
                await install_role(role_name="ludus-ad-content")
        """
        # Initialize RoleManager (no SSH needed for checking)
        role_manager = RoleManager(client)
        try:
            is_installed = await role_manager.check_role_installed(role_name)
            return format_tool_response({
                "status": "success",
                "role_name": role_name,
                "installed": is_installed,
            })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "role_name": role_name,
                "error": str(e),
            })

    @mcp.tool()
    async def install_role(
        role_name: str,
        role_url: str | None = None,
        max_retries: int = 3,
    ) -> dict:
        """Install an Ansible role on the Ludus server via MCP.

        This MCP tool automatically handles:
        - Galaxy roles (installed directly from Ansible Galaxy, e.g., "badsectorlabs.ludus_adcs")
        - Directory-based roles (automatically cloned via SSH if configured, e.g., "ludus-ad-content")
        - Retry logic for transient failures

        **For directory-based roles**: If SSH is configured (via `configure_ssh_role_installation`),
        the MCP server will automatically clone the repository on the Ludus server and install it.
        Otherwise, manual installation instructions will be provided.

        Args:
            role_name: Name of the role to install (e.g., "badsectorlabs.ludus_adcs", "aleemladha.wazuh_server_install")
            role_url: Optional URL for Galaxy roles (usually not needed)
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Installation result with status and details

        Example:
            # Install a Galaxy role (works immediately)
            result = await install_role(role_name="badsectorlabs.ludus_adcs")
            
            # Install a directory-based role (requires SSH config or manual setup)
            result = await install_role(role_name="ludus-ad-content")
            
            # Check installation status
            status = await check_role_installed(role_name="badsectorlabs.ludus_adcs")
        """
        # Initialize RoleManager with SSH configuration from environment
        role_manager = RoleManager(
            client,
            ssh_host=os.getenv("LUDUS_SSH_HOST"),
            ssh_user=os.getenv("LUDUS_SSH_USER"),
            ssh_key_path=os.getenv("LUDUS_SSH_KEY_PATH"),
            ssh_password=os.getenv("LUDUS_SSH_PASSWORD"),
            allow_ssh_install=os.getenv("LUDUS_ALLOW_SSH_INSTALL", "false").lower() == "true",
        )
        try:
            # Check if already installed
            is_installed = await role_manager.check_role_installed(role_name)
            if is_installed:
                return format_tool_response({
                    "status": "already_installed",
                    "role_name": role_name,
                    "message": f"Role {role_name} is already installed",
                })
            
            # Attempt installation
            logger.info(f"Installing role: {role_name}")
            install_result = await role_manager.install_role(
                role_name, role_url=role_url, max_retries=max_retries
            )
            
            # Verify installation
            is_now_installed = await role_manager.check_role_installed(role_name)
            
            if is_now_installed:
                return format_tool_response({
                    "status": "success",
                    "role_name": role_name,
                    "message": f"Successfully installed role: {role_name}",
                    "install_result": install_result,
                })
            else:
                # Installation may have reported success but role not found
                # This can happen with directory-based roles
                if install_result.get("status") == "manual_installation_required":
                    return format_tool_response({
                        "status": "manual_installation_required",
                        "role_name": role_name,
                        "message": f"Role {role_name} requires manual setup on Ludus server",
                        "command": install_result.get("command", ""),
                        "directory": install_result.get("directory", ""),
                        "note": install_result.get("note", ""),
                    })
                else:
                    return format_tool_response({
                        "status": "warning",
                        "role_name": role_name,
                        "message": f"Installation reported success but role not found. May need manual verification.",
                        "install_result": install_result,
                    })
        except Exception as e:
            error_msg = str(e)
            # Check if it's a directory-based role that needs manual setup
            if role_name in role_manager.ROLE_REPOSITORIES:
                repo_url = role_manager.ROLE_REPOSITORIES[role_name][0]
                server_path = f"{role_manager.SERVER_ROLES_PATH}/{role_name}"
                return format_tool_response({
                    "status": "manual_installation_required",
                    "role_name": role_name,
                    "error": error_msg,
                    "message": f"Role {role_name} must be cloned on Ludus server first",
                    "instructions": [
                        f"1. SSH to Ludus server",
                        f"2. cd {role_manager.SERVER_ROLES_PATH}",
                        f"3. git clone {repo_url} {role_name}",
                        f"4. ludus ansible role add -d {server_path}",
                    ],
                    "repository_url": repo_url,
                    "server_path": server_path,
                })
            
            # Provide helpful error message with suggestions
            return format_tool_response({
                "status": "error",
                "role_name": role_name,
                "error": error_msg,
                "suggestions": [
                    "Verify the role name is correct (check Ansible Galaxy or Ludus documentation)",
                    "For Galaxy roles, use format: namespace.role_name (e.g., badsectorlabs.ludus_adcs)",
                    "For directory-based roles, ensure SSH is configured or follow manual instructions",
                    "Use list_installed_roles() to see what roles are currently available",
                    "Check Ludus documentation: https://docs.ludus.cloud/docs/roles/",
                ],
            })

    @mcp.tool()
    async def get_required_roles_for_scenario(
        scenario_key: str,
        siem_type: str = "wazuh",
    ) -> dict:
        """Get the list of required Ansible roles for a specific scenario.

        Use this MCP tool to check which roles are needed before deploying a scenario.
        Then use `ensure_scenario_roles()` to automatically install missing roles.

        Args:
            scenario_key: Scenario identifier (e.g., "redteam-lab-intermediate")
            siem_type: SIEM type if scenario uses SIEM (wazuh, splunk, elastic, security-onion, none)

        Returns:
            Dictionary with required roles and their installation status

        Example:
            # Check required roles for a scenario
            result = await get_required_roles_for_scenario(
                scenario_key="redteam-lab-intermediate",
                siem_type="none"
            )
            
            # Then ensure all roles are installed
            await ensure_scenario_roles(
                scenario_key="redteam-lab-intermediate",
                siem_type="none",
                auto_install=True
            )
        """
        # Initialize RoleManager with SSH configuration from environment
        role_manager = RoleManager(
            client,
            ssh_host=os.getenv("LUDUS_SSH_HOST"),
            ssh_user=os.getenv("LUDUS_SSH_USER"),
            ssh_key_path=os.getenv("LUDUS_SSH_KEY_PATH"),
            ssh_password=os.getenv("LUDUS_SSH_PASSWORD"),
            allow_ssh_install=os.getenv("LUDUS_ALLOW_SSH_INSTALL", "false").lower() == "true",
        )
        try:
            # Get required roles
            scenario_config = await _scenario_config(client, scenario_key, siem_type)
            role_status = await role_manager.ensure_roles_for_scenario(
                scenario_key, auto_install=False, siem_type=siem_type, config=scenario_config
            )
            
            return format_tool_response({
                "status": "success",
                "scenario_key": scenario_key,
                "siem_type": siem_type,
                "required_roles": role_status.get("required_roles", []),
                "installed": role_status.get("installed", []),
                "missing": role_status.get("missing", []),
                "count": {
                    "total": len(role_status.get("required_roles", [])),
                    "installed": len(role_status.get("installed", [])),
                    "missing": len(role_status.get("missing", [])),
                },
            })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "scenario_key": scenario_key,
                "error": str(e),
            })

    @mcp.tool()
    async def configure_ssh_role_installation(
        ssh_host: str,
        ssh_user: str = "root",
        ssh_key_path: str | None = None,
        ssh_password: str | None = None,
        allow_ssh_install: bool = True,
    ) -> dict:
        """Configure SSH access for automatic role installation on Ludus server.
        
        This allows the MCP server to automatically clone and install directory-based roles
        (like ludus-ad-content) directly on the Ludus server via SSH, without manual setup.
        
        **Security Note:** SSH access requires appropriate permissions. Use SSH keys when possible.
        
        Args:
            ssh_host: SSH hostname or IP address of the Ludus server
            ssh_user: SSH username (default: "root")
            ssh_key_path: Path to SSH private key file (preferred over password)
            ssh_password: SSH password (less secure, only use if key is not available)
            allow_ssh_install: Enable automatic SSH-based installation (default: True)
        
        Returns:
            Configuration result with status
        
        Example:
            # Configure with SSH key (recommended)
            result = await configure_ssh_role_installation(
                ssh_host="198.51.100.1",
                ssh_user="root",
                ssh_key_path="~/.ssh/id_rsa",
                allow_ssh_install=True
            )
            
            # Configure with password (less secure)
            result = await configure_ssh_role_installation(
                ssh_host="198.51.100.1",
                ssh_user="root",
                ssh_password="your-password",
                allow_ssh_install=True
            )
        """
        import os
        
        try:
            # Set environment variables for SSH configuration
            os.environ["LUDUS_SSH_HOST"] = ssh_host
            os.environ["LUDUS_SSH_USER"] = ssh_user
            if ssh_key_path:
                os.environ["LUDUS_SSH_KEY_PATH"] = ssh_key_path
                if "LUDUS_SSH_PASSWORD" in os.environ:
                    del os.environ["LUDUS_SSH_PASSWORD"]  # Remove password if key is provided
            elif ssh_password:
                os.environ["LUDUS_SSH_PASSWORD"] = ssh_password
                if "LUDUS_SSH_KEY_PATH" in os.environ:
                    del os.environ["LUDUS_SSH_KEY_PATH"]  # Remove key if password is provided
            else:
                return format_tool_response({
                    "status": "error",
                    "error": "Either ssh_key_path or ssh_password must be provided",
                })
            
            os.environ["LUDUS_ALLOW_SSH_INSTALL"] = "true" if allow_ssh_install else "false"
            
            # Test SSH connection
            if allow_ssh_install:
                role_manager = RoleManager(
                    client,
                    ssh_host=ssh_host,
                    ssh_user=ssh_user,
                    ssh_key_path=ssh_key_path,
                    ssh_password=ssh_password,
                    allow_ssh_install=True,
                )
                
                # Simple connectivity test
                import subprocess
                ssh_cmd = ["ssh"]
                if ssh_key_path:
                    ssh_cmd.extend(["-i", ssh_key_path])
                ssh_cmd.extend([
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=5",
                    f"{ssh_user}@{ssh_host}",
                    "echo 'SSH connection successful'"
                ])
                
                if ssh_password and not ssh_key_path:
                    ssh_cmd = ["sshpass", "-p", ssh_password] + ssh_cmd
                
                try:
                    result = subprocess.run(
                        ssh_cmd,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    ssh_test = "success"
                    ssh_message = "SSH connection test successful"
                except Exception as e:
                    ssh_test = "warning"
                    ssh_message = f"SSH connection test failed: {e}. Configuration saved but may not work."
            else:
                ssh_test = "skipped"
                ssh_message = "SSH installation disabled"
            
            return format_tool_response({
                "status": "success",
                "ssh_host": ssh_host,
                "ssh_user": ssh_user,
                "ssh_key_path": ssh_key_path if ssh_key_path else "Not set (using password)",
                "allow_ssh_install": allow_ssh_install,
                "ssh_test": ssh_test,
                "message": f"SSH configuration saved. {ssh_message}",
                "note": "Configuration is stored in environment variables for this session. "
                       "To persist, set these in your MCP server environment or .env file.",
            })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "error": str(e),
            })

    @mcp.tool()
    async def ensure_scenario_roles(
        scenario_key: str,
        siem_type: str = "wazuh",
        auto_install: bool = True,
    ) -> dict:
        """Ensure all required roles for a scenario are installed, installing missing ones automatically.

        **This is the recommended MCP tool to use before deploying a scenario.** It will:
        1. Check which roles are required for the scenario
        2. Check which roles are already installed
        3. Automatically install missing Galaxy roles (if auto_install=True)
        4. Automatically clone and install directory-based roles via SSH (if SSH configured)
        5. Report which roles need manual installation (if SSH not configured)
        
        **MCP Workflow**:
        - Use `ensure_scenario_roles()` before deploying to ensure all roles are ready
        - Configure SSH access with `configure_ssh_role_installation()` for automatic directory-based role installation
        - Use `install_role()` to install individual roles as needed

        Args:
            scenario_key: Scenario identifier (e.g., "redteam-lab-intermediate")
            siem_type: SIEM type if scenario uses SIEM (wazuh, splunk, elastic, security-onion, none)
            auto_install: Automatically install missing roles (default: True)

        Returns:
            Dictionary with installation status for all required roles

        Example:
            # Ensure all roles are installed before deployment
            result = await ensure_scenario_roles(
                scenario_key="redteam-lab-intermediate",
                siem_type="none",
                auto_install=True
            )
            
            # Check status without installing
            result = await ensure_scenario_roles(
                scenario_key="redteam-lab-intermediate",
                auto_install=False
            )
        """
        role_manager = RoleManager(client)
        try:
            logger.info(f"Ensuring roles for scenario: {scenario_key} (SIEM: {siem_type}, auto_install: {auto_install})")
            
            scenario_config = await _scenario_config(client, scenario_key, siem_type)
            role_status = await role_manager.ensure_roles_for_scenario(
                scenario_key, auto_install=auto_install, siem_type=siem_type, config=scenario_config
            )
            
            # Format the response
            result = {
                "status": role_status.get("status", "checked"),
                "scenario_key": scenario_key,
                "siem_type": siem_type,
                "required_roles": role_status.get("required_roles", []),
                "installed": role_status.get("installed", []),
                "missing": role_status.get("missing", []),
                "install_attempted": role_status.get("install_attempted", []),
                "install_failed": role_status.get("install_failed", []),
                "count": {
                    "total": len(role_status.get("required_roles", [])),
                    "installed": len(role_status.get("installed", [])),
                    "missing": len(role_status.get("missing", [])),
                    "install_attempted": len(role_status.get("install_attempted", [])),
                    "install_failed": len(role_status.get("install_failed", [])),
                },
            }
            
            # Add helpful messages
            if role_status.get("install_failed"):
                result["manual_installation_required"] = []
                for failed in role_status["install_failed"]:
                    role_name = failed.get("role", "unknown")
                    if role_name in role_manager.ROLE_REPOSITORIES:
                        repo_url = role_manager.ROLE_REPOSITORIES[role_name][0]
                        server_path = f"{role_manager.SERVER_ROLES_PATH}/{role_name}"
                        result["manual_installation_required"].append({
                            "role": role_name,
                            "repository_url": repo_url,
                            "server_path": server_path,
                            "command": f"cd {role_manager.SERVER_ROLES_PATH} && git clone {repo_url} {role_name} && ludus ansible role add -d {server_path}",
                            "error": failed.get("error", ""),
                        })
            
            if not result["missing"] and not result["install_failed"]:
                result["message"] = "All required roles are installed and ready"
            elif result["missing"]:
                result["message"] = f"{len(result['missing'])} roles are missing. Set auto_install=True to install them."
            elif result["install_failed"]:
                result["message"] = f"{len(result['install_failed'])} roles require manual installation on Ludus server."
            
            return format_tool_response(result)
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "scenario_key": scenario_key,
                "error": str(e),
            })

    @mcp.tool()
    async def get_role_info(role_name: str) -> dict:
        """Get information about a specific role, including installation method and requirements.

        Uses the ludus CLI with --url when available for reliable remote access.
        No SSH required for checking role information.

        Args:
            role_name: Name of the role to get information about

        Returns:
            Dictionary with role information, installation method, and instructions

        Example:
            # Get info about a Galaxy role
            info = await get_role_info(role_name="badsectorlabs.ludus_adcs")

            # Get info about a directory-based role
            info = await get_role_info(role_name="ludus-ad-vulns")
        """
        # Initialize RoleManager (no SSH needed for info checking)
        role_manager = RoleManager(client)
        
        try:
            # Check if it's a directory-based role
            is_directory_based = role_name in role_manager.ROLE_REPOSITORIES
            is_installed = await role_manager.check_role_installed(role_name)
            
            info = {
                "status": "success",
                "role_name": role_name,
                "installed": is_installed,
                "installation_method": "directory" if is_directory_based else "galaxy",
            }
            
            if is_directory_based:
                repo_info = role_manager.ROLE_REPOSITORIES[role_name]
                if isinstance(repo_info, tuple):
                    repo_url, subdirectory = repo_info
                else:
                    repo_url = repo_info
                    subdirectory = None
                
                info.update({
                    "repository_url": repo_url,
                    "subdirectory": subdirectory,
                    "server_path": f"{role_manager.SERVER_ROLES_PATH}/{role_name}",
                    "installation_instructions": [
                        "This role must be installed from a local directory",
                        "The MCP server can automatically clone and install it if SSH is configured",
                        f"Repository: {repo_url}",
                        f"Expected path on Ludus server: {role_manager.SERVER_ROLES_PATH}/{role_name}",
                    ],
                    "mcp_installation": {
                        "requires_ssh": True,
                        "automatic_if_ssh_configured": True,
                        "manual_command": f"cd {role_manager.SERVER_ROLES_PATH} && git clone {repo_url} {role_name} && ludus ansible role add -d {role_manager.SERVER_ROLES_PATH}/{role_name}",
                    },
                })
            else:
                info.update({
                    "installation_instructions": [
                        "This role can be installed directly from Ansible Galaxy",
                        "The MCP server can install it automatically via the Ludus API",
                    ],
                    "mcp_installation": {
                        "requires_ssh": False,
                        "automatic_if_ssh_configured": False,
                        "command": f"await install_role(role_name='{role_name}')",
                    },
                })
            
            return format_tool_response(info)
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "role_name": role_name,
                "error": str(e),
            })

    @mcp.tool()
    async def install_galaxy_role(
        role_name: str,
        version: str | None = None,
    ) -> dict:
        """Install an Ansible role directly from Ansible Galaxy.

        This is the simplest way to install roles. Provide the Galaxy role name
        in the format 'namespace.role_name' and it will be installed on the Ludus server.

        Args:
            role_name: Role name in Galaxy format (e.g., "geerlingguy.docker", "badsectorlabs.ludus_adcs")
            version: Optional version to install (e.g., "1.0.0")

        Returns:
            Installation result with status

        Examples:
            # Install a role from Ansible Galaxy
            result = await install_galaxy_role(role_name="geerlingguy.docker")

            # Install a specific version
            result = await install_galaxy_role(role_name="geerlingguy.docker", version="6.1.0")

            # Install common Ludus roles
            await install_galaxy_role(role_name="badsectorlabs.ludus_adcs")
            await install_galaxy_role(role_name="aleemladha.wazuh_server_install")

        Common Galaxy roles for Ludus:
            - badsectorlabs.ludus_adcs: AD Certificate Services
            - badsectorlabs.ludus_mssql: SQL Server
            - badsectorlabs.ludus_commandovm: Commando VM setup
            - badsectorlabs.ludus_flarevm: Flare VM setup
            - badsectorlabs.ludus_remnux: REMnux setup
            - aleemladha.wazuh_server_install: Wazuh server
            - aleemladha.ludus_wazuh_agent: Wazuh agent
            - geerlingguy.docker: Docker installation
        """
        # Initialize RoleManager (no SSH needed for Galaxy roles)
        role_manager = RoleManager(client)

        try:
            # Check if already installed
            is_installed = await role_manager.check_role_installed(role_name)
            if is_installed:
                return format_tool_response({
                    "status": "already_installed",
                    "role_name": role_name,
                    "message": f"Role {role_name} is already installed",
                })

            # Build role specification with version if provided
            role_spec = role_name
            if version:
                role_spec = f"{role_name},{version}"

            # Install from Galaxy via API
            logger.info(f"Installing Galaxy role: {role_spec}")
            config = {
                "action": "install",
                "name": role_name,
            }

            result = await client.install_ansible_role(config)

            # Verify installation
            is_now_installed = await role_manager.check_role_installed(role_name)

            if is_now_installed:
                return format_tool_response({
                    "status": "success",
                    "role_name": role_name,
                    "version": version,
                    "message": f"Successfully installed role: {role_name}",
                })
            else:
                return format_tool_response({
                    "status": "warning",
                    "role_name": role_name,
                    "message": "Installation completed but role not found in list. May need verification.",
                })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "role_name": role_name,
                "error": str(e),
                "suggestion": "Verify the role name exists on Ansible Galaxy: https://galaxy.ansible.com/",
            })

    @mcp.tool()
    async def install_role_from_url(
        role_name: str,
        git_url: str,
        branch: str | None = None,
    ) -> dict:
        """Install an Ansible role from a custom Git repository URL.

        Use this to install roles from custom Git repositories that are not on
        Ansible Galaxy. The repository will be cloned on the Ludus server and installed.

        Args:
            role_name: Name to give the role when installed
            git_url: Git repository URL (e.g., "https://github.com/user/my-role")
            branch: Optional branch/tag to checkout (default: main/master)

        Returns:
            Installation result with status and instructions

        Examples:
            # Install a custom role from GitHub
            result = await install_role_from_url(
                role_name="my-custom-role",
                git_url="https://github.com/myorg/ludus-custom-role"
            )

            # Install from a specific branch
            result = await install_role_from_url(
                role_name="my-role-dev",
                git_url="https://github.com/myorg/ludus-custom-role",
                branch="develop"
            )
        """
        role_manager = RoleManager(
            client,
            ssh_host=os.getenv("LUDUS_SSH_HOST"),
            ssh_user=os.getenv("LUDUS_SSH_USER"),
            ssh_key_path=os.getenv("LUDUS_SSH_KEY_PATH"),
            ssh_password=os.getenv("LUDUS_SSH_PASSWORD"),
            allow_ssh_install=os.getenv("LUDUS_ALLOW_SSH_INSTALL", "false").lower() == "true",
        )

        server_path = f"{role_manager.SERVER_ROLES_PATH}/{role_name}"

        # Build clone command with optional branch
        if branch:
            clone_cmd = f"git clone -b {branch} {git_url} {role_name}"
        else:
            clone_cmd = f"git clone {git_url} {role_name}"

        try:
            # Try SSH-based installation if configured
            if role_manager.allow_ssh_install and role_manager.ssh_host:
                logger.info(f"Installing custom role {role_name} from {git_url} via SSH")

                import subprocess

                # Build SSH command
                ssh_cmd = ["ssh"]
                if role_manager.ssh_key_path:
                    ssh_cmd.extend(["-i", role_manager.ssh_key_path])
                ssh_cmd.extend([
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "ConnectTimeout=10",
                ])

                # Build remote command
                remote_cmd = f"cd {role_manager.SERVER_ROLES_PATH} && {clone_cmd} && ludus ansible role add -d {server_path}"

                if role_manager.ssh_password and not role_manager.ssh_key_path:
                    ssh_cmd = ["sshpass", "-p", role_manager.ssh_password] + ssh_cmd

                ssh_cmd.append(f"{role_manager.ssh_user}@{role_manager.ssh_host}")
                ssh_cmd.append(remote_cmd)

                result = subprocess.run(
                    ssh_cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=180
                )

                # Verify installation
                is_installed = await role_manager.check_role_installed(role_name)

                return format_tool_response({
                    "status": "success" if is_installed else "warning",
                    "role_name": role_name,
                    "git_url": git_url,
                    "branch": branch,
                    "server_path": server_path,
                    "installed": is_installed,
                    "message": f"Role {role_name} installed from {git_url}",
                })
            else:
                # Return manual installation instructions
                return format_tool_response({
                    "status": "manual_installation_required",
                    "role_name": role_name,
                    "git_url": git_url,
                    "branch": branch,
                    "server_path": server_path,
                    "message": "SSH not configured. Install manually on Ludus server.",
                    "instructions": [
                        f"1. SSH to Ludus server",
                        f"2. cd {role_manager.SERVER_ROLES_PATH}",
                        f"3. {clone_cmd}",
                        f"4. ludus ansible role add -d {server_path}",
                    ],
                    "command": f"cd {role_manager.SERVER_ROLES_PATH} && {clone_cmd} && ludus ansible role add -d {server_path}",
                })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "role_name": role_name,
                "git_url": git_url,
                "error": str(e),
                "manual_command": f"cd {role_manager.SERVER_ROLES_PATH} && {clone_cmd} && ludus ansible role add -d {server_path}",
            })

    @mcp.tool()
    async def get_common_galaxy_roles() -> dict:
        """Get a list of commonly used Ansible Galaxy roles for Ludus scenarios.

        Returns a curated list of Galaxy roles that are frequently used in security
        lab scenarios, along with their descriptions and example usage.

        Returns:
            Dictionary of common roles organized by category

        Example:
            roles = await get_common_galaxy_roles()
            # Then install what you need:
            await install_galaxy_role(role_name="geerlingguy.docker")
        """
        return format_tool_response({
            "status": "success",
            "categories": {
                "ludus_official": {
                    "description": "Official Ludus roles from Bad Sector Labs",
                    "roles": [
                        {"name": "badsectorlabs.ludus_adcs", "description": "AD Certificate Services for ESC attacks"},
                        {"name": "badsectorlabs.ludus_mssql", "description": "Microsoft SQL Server installation"},
                        {"name": "badsectorlabs.ludus_commandovm", "description": "Commando VM offensive tools"},
                        {"name": "badsectorlabs.ludus_flarevm", "description": "Flare VM malware analysis tools"},
                        {"name": "badsectorlabs.ludus_remnux", "description": "REMnux Linux malware analysis"},
                        {"name": "badsectorlabs.ludus_elastic_container", "description": "Elastic Stack container"},
                        {"name": "badsectorlabs.ludus_elastic_agent", "description": "Elastic agent for monitoring"},
                    ],
                },
                "siem_monitoring": {
                    "description": "SIEM and monitoring roles",
                    "roles": [
                        {"name": "aleemladha.wazuh_server_install", "description": "Wazuh SIEM server"},
                        {"name": "aleemladha.ludus_wazuh_agent", "description": "Wazuh agent for endpoints"},
                    ],
                },
                "infrastructure": {
                    "description": "Common infrastructure roles",
                    "roles": [
                        {"name": "geerlingguy.docker", "description": "Docker installation and config"},
                        {"name": "geerlingguy.nginx", "description": "Nginx web server"},
                        {"name": "geerlingguy.postgresql", "description": "PostgreSQL database"},
                        {"name": "geerlingguy.redis", "description": "Redis cache server"},
                        {"name": "geerlingguy.java", "description": "Java JDK installation"},
                        {"name": "geerlingguy.nodejs", "description": "Node.js installation"},
                    ],
                },
                "security_tools": {
                    "description": "Security and pentesting tools",
                    "roles": [
                        {"name": "dev-sec.os-hardening", "description": "OS hardening baseline"},
                        {"name": "dev-sec.ssh-hardening", "description": "SSH hardening"},
                    ],
                },
            },
            "usage": "Use install_galaxy_role(role_name='...') to install any of these roles",
        })

    @mcp.tool()
    async def list_role_repositories() -> dict:
        """List all roles that are available from GitHub repositories (directory-based roles).

        These roles must be cloned on the Ludus server before installation.

        Returns:
            Dictionary with available role repositories and their GitHub URLs

        Example:
            result = await list_role_repositories()
        """
        # Initialize RoleManager (no SSH needed for listing)
        role_manager = RoleManager(client)
        try:
            repositories = []
            for role_name, repo_info in role_manager.ROLE_REPOSITORIES.items():
                if isinstance(repo_info, tuple):
                    repo_url, subdirectory = repo_info
                else:
                    repo_url = repo_info
                    subdirectory = None
                
                repositories.append({
                    "role_name": role_name,
                    "repository_url": repo_url,
                    "subdirectory": subdirectory,
                    "server_path": f"{role_manager.SERVER_ROLES_PATH}/{role_name}",
                    "installation_command": f"cd {role_manager.SERVER_ROLES_PATH} && git clone {repo_url} {role_name} && ludus ansible role add -d {role_manager.SERVER_ROLES_PATH}/{role_name}",
                })
            
            return format_tool_response({
                "status": "success",
                "repositories": repositories,
                "count": len(repositories),
                "note": "These roles must be cloned on the Ludus server before installation",
            })
        except Exception as e:
            return format_tool_response({
                "status": "error",
                "error": str(e),
            })

    return mcp


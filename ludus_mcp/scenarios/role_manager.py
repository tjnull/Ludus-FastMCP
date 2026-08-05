"""Manager for ensuring Ludus roles are installed."""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class RoleManager:
    """Manages Ludus Ansible role installation."""

    # Roles that need to be cloned from GitHub before installation
    # These roles must be installed from local directories
    # See: https://docs.ludus.cloud/docs/roles/
    # Format: "role_name": ("repository_url", "subdirectory_path" or None)
    ROLE_REPOSITORIES = {
        # AD Roles - These must be cloned on Ludus server and installed from directory
        # Expected location: /opt/ludus/roles/<role-name>/
        "ludus-ad-content": ("https://github.com/Cyblex-Consulting/ludus-ad-content", None),
        "ludus-ad-vulns": ("https://github.com/Primusinterp/ludus-ad-vulns", None),
        "ludus_child_domain": ("https://github.com/ChoiSG/ludus_ansible_roles", None),
        "ludus_badblood": ("https://github.com/curi0usJack/ludus_badblood", None),
        "ludus-local-users": ("https://github.com/Cyblex-Consulting/ludus-local-users", None),
        
        # Security & Monitoring Roles
        "ludus_graylog_server": ("https://github.com/frack113/my-ludus-roles", None),
        "ludus_enable_asr": ("https://github.com/curi0usJack/Ludus-MDE-MDI-Roles", "ludus_enable_asr"),
        "ludus_enable_mdi_gpo": ("https://github.com/curi0usJack/Ludus-MDE-MDI-Roles", "ludus_enable_mdi_gpo"),
        
        # Web Application Roles
        "ludus_juiceshop": ("https://github.com/xurger/ludus_juiceshop", None),
        
        # Additional roles from Ludus documentation that require directory installation
        # See: https://docs.ludus.cloud/docs/roles/
        "ludus_aurora_agent": ("https://github.com/frack113/ludus_aurora_agent", None),
        "ludus_filigran_opencti": ("https://github.com/frack113/ludus_filigran_opencti", None),
        "ludus_ghosts_server": ("https://github.com/frack113/ludus_ghosts_server", None),
        "ludus_adtimeline_syncthing": ("https://github.com/mojeda101/ludus_adtimeline_syncthing", None),
        "ludus_litterbox": ("https://github.com/professor-moody/ludus_litterbox_role", None),
        "ludus_nemesis": ("https://github.com/brmkit/ludus_nemesis", None),
        "ludus_guacamole": ("https://github.com/brmkit/ludus_guacamole", None),
    }
    
    # Default server-side path for cloned roles
    # Roles should be cloned to /opt/ludus/roles/ on the Ludus server
    SERVER_ROLES_PATH = "/opt/ludus/roles"
    
    # Common roles needed for scenarios
    # Note: Templates already have Windows/Linux systems built
    # These roles are for services that need to be installed on top
    # See: https://docs.ludus.cloud/docs/roles/
    REQUIRED_ROLES = {
        "ad": [
            # AD roles that need to be cloned and installed from local directories
            "ludus-ad-content",  # Creates AD structure (OUs, groups, users)
            "ludus-ad-vulns",   # Adds vulnerabilities to AD
        ],
        "ad-intermediate": [
            # Additional roles for intermediate/advanced AD scenarios
            "ludus-ad-content",
            "ludus-ad-vulns",
            "badsectorlabs.ludus_adcs",  # AD Certificate Services
        ],
        "ad-advanced": [
            # Additional roles for advanced AD scenarios
            "ludus-ad-content",
            "ludus-ad-vulns",
            "badsectorlabs.ludus_adcs",  # AD Certificate Services
            "ludus_child_domain",  # Child domain creation
        ],
        "sql": [
            # SQL Server roles
            "badsectorlabs.ludus_mssql",  # SQL Server installation
        ],
        "template": [
            # Roles for building custom templates
            "badsectorlabs.ludus_commandovm",  # Sets up Commando VM on Windows >= 10
            "badsectorlabs.ludus_flarevm",     # Installs Flare VM on Windows >= 10
            "badsectorlabs.ludus_remnux",      # Installs REMnux on Ubuntu 20.04
        ],
        "web": [
            # Web service roles added in scenario builders if needed
        ],
        "network": [
            # Network roles added in scenario builders if needed
        ],
        "purple-team": [
            # Purple team specific roles added in scenario builders
        ],
        "wazuh": [
            "aleemladha.wazuh_server_install",  # Wazuh server role from Ludus docs
            "aleemladha.ludus_wazuh_agent",    # Wazuh agent role from Ludus docs
        ],
        "splunk": [
            # Splunk roles added in scenario builders if needed
        ],
        "elastic": [
            "badsectorlabs.ludus_elastic_container",  # Elastic container from Ludus docs
            "badsectorlabs.ludus_elastic_agent",      # Elastic agent from Ludus docs
        ],
        "security-onion": [
            # Security Onion roles added in scenario builders if needed
        ],
        "goad": [
            # GOAD scenarios use templates, no additional roles needed
        ],
    }

    def __init__(
        self,
        client: LudusAPIClient,
        roles_cache_dir: str | None = None,
        ssh_host: str | None = None,
        ssh_user: str | None = None,
        ssh_key_path: str | None = None,
        ssh_password: str | None = None,
        allow_ssh_install: bool = False,
    ):
        """Initialize the role manager.
        
        Args:
            client: Ludus API client
            roles_cache_dir: Directory to cache cloned role repositories (default: ~/.ludus/roles)
            ssh_host: SSH hostname/IP for Ludus server (optional, for automatic role installation)
            ssh_user: SSH username for Ludus server (optional)
            ssh_key_path: Path to SSH private key (optional, preferred over password)
            ssh_password: SSH password (optional, less secure than key)
            allow_ssh_install: Allow automatic installation via SSH (default: False, requires explicit permission)
        """
        self.client = client
        if roles_cache_dir:
            self.roles_cache_dir = Path(roles_cache_dir)
        else:
            # Default to ~/.ludus/roles
            self.roles_cache_dir = Path.home() / ".ludus" / "roles"
        self.roles_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # SSH configuration for automatic role installation on Ludus server
        self.ssh_host = ssh_host or os.getenv("LUDUS_SSH_HOST")
        self.ssh_user = ssh_user or os.getenv("LUDUS_SSH_USER", "root")
        self.ssh_key_path = ssh_key_path or os.getenv("LUDUS_SSH_KEY_PATH")
        self.ssh_password = ssh_password or os.getenv("LUDUS_SSH_PASSWORD")
        self.allow_ssh_install = allow_ssh_install or os.getenv("LUDUS_ALLOW_SSH_INSTALL", "false").lower() == "true"
        
        # Validate SSH configuration if enabled
        if self.allow_ssh_install:
            if not self.ssh_host:
                logger.warning(
                    "SSH installation enabled but LUDUS_SSH_HOST not set. "
                    "Automatic role installation via SSH will be disabled."
                )
                self.allow_ssh_install = False
            elif not self.ssh_key_path and not self.ssh_password:
                logger.warning(
                    "SSH installation enabled but neither LUDUS_SSH_KEY_PATH nor LUDUS_SSH_PASSWORD set. "
                    "Automatic role installation via SSH will be disabled."
                )
                self.allow_ssh_install = False

    async def get_installed_roles(self) -> list[dict]:
        """Get list of all installed roles.

        Prefers using the ludus CLI with --url for reliable remote checking.
        Falls back to HTTP API if CLI is not available.

        Returns:
            List of role dictionaries with name, version, and global status
        """
        import shutil
        import subprocess
        from ludus_mcp.utils.config import get_settings

        settings = get_settings()

        # Prefer ludus CLI if available (works both locally and remotely with --url)
        ludus_cli = shutil.which("ludus")
        if ludus_cli and settings.ludus_api_key:
            try:
                env = os.environ.copy()
                env["LUDUS_API_KEY"] = settings.ludus_api_key

                result = subprocess.run(
                    ["ludus", "ansible", "roles", "list", "--url", settings.ludus_api_url],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )

                if result.returncode == 0:
                    output = result.stdout + result.stderr
                    roles = []
                    # Parse the table output
                    # Format: |  NAME  | VERSION | GLOBAL |
                    for line in output.split('\n'):
                        if '|' in line:
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            # Skip header row and separator rows
                            if len(parts) >= 3 and parts[0] not in ('NAME', '+', '-'):
                                if not parts[0].startswith('-') and not parts[0].startswith('+'):
                                    roles.append({
                                        "name": parts[0],
                                        "version": parts[1] if len(parts) > 1 else None,
                                        "global": parts[2].lower() == "true" if len(parts) > 2 else False,
                                        "type": "role",
                                    })
                    return roles
            except subprocess.TimeoutExpired:
                logger.warning("Timeout listing roles via CLI, falling back to API")
            except Exception as e:
                logger.warning(f"Error listing roles via CLI: {e}, falling back to API")

        # Fallback to HTTP API
        try:
            ansible_resources = await self.client.list_ansible_resources()
            if isinstance(ansible_resources, dict):
                roles = ansible_resources.get("roles", [])
            elif isinstance(ansible_resources, list):
                roles = ansible_resources
            else:
                roles = []

            # Normalize role format
            formatted_roles = []
            for role in roles:
                if isinstance(role, str):
                    formatted_roles.append({"name": role, "type": "role"})
                elif isinstance(role, dict):
                    formatted_roles.append({
                        "name": role.get("Name") or role.get("name", "unknown"),
                        "version": role.get("Version") or role.get("version"),
                        "type": role.get("Type") or role.get("type", "role"),
                        "global": role.get("Global") or role.get("global", False),
                    })
            return formatted_roles
        except Exception as e:
            logger.warning(f"Error listing roles: {e}")
            return []

    async def check_role_installed(self, role_name: str) -> bool:
        """Check if a role is installed.

        Prefers using the ludus CLI with --url for reliable remote checking.
        Falls back to HTTP API if CLI is not available.

        The API returns roles as a list of dicts with capital "Name" key:
        [{"Name": "role-name", "Version": "...", "Type": "role", "Global": False}, ...]
        """
        import shutil
        import subprocess
        from ludus_mcp.utils.config import get_settings

        settings = get_settings()

        # Prefer ludus CLI if available (works both locally and remotely with --url)
        ludus_cli = shutil.which("ludus")
        if ludus_cli and settings.ludus_api_key:
            try:
                env = os.environ.copy()
                env["LUDUS_API_KEY"] = settings.ludus_api_key

                result = subprocess.run(
                    ["ludus", "ansible", "roles", "list", "--url", settings.ludus_api_url],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )

                if result.returncode == 0:
                    output = result.stdout + result.stderr
                    # Parse the table output - role names are in the first column
                    # Format: |  role-name  | version | global |
                    for line in output.split('\n'):
                        if '|' in line and role_name in line:
                            # Extract the role name from the table row
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            if parts and parts[0] == role_name:
                                return True
                    return False
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout checking role {role_name} via CLI, falling back to API")
            except Exception as e:
                logger.warning(f"Error checking role via CLI: {e}, falling back to API")

        # Fallback to HTTP API
        try:
            ansible_resources = await self.client.list_ansible_resources()
            # API returns roles as a list or dict, check both formats
            if isinstance(ansible_resources, dict):
                roles = ansible_resources.get("roles", [])
            elif isinstance(ansible_resources, list):
                roles = ansible_resources
            else:
                roles = []

            # Check if role exists (could be string or dict)
            for role in roles:
                if isinstance(role, str):
                    if role == role_name:
                        return True
                elif isinstance(role, dict):
                    # API returns capital "Name" key, but check both for compatibility
                    role_name_in_dict = (
                        role.get("Name") or  # Capital N (actual API format)
                        role.get("name") or  # Lowercase n (fallback)
                        role.get("role")     # Alternative key
                    )
                    if role_name_in_dict == role_name:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking role {role_name}: {e}")
            return False

    async def clone_role_on_server_via_ssh(self, role_name: str) -> dict[str, Any]:
        """Clone a role repository directly on the Ludus server via SSH.
        
        This method requires SSH access to the Ludus server and will clone
        the repository to /opt/ludus/roles/<role-name> on the server.
        
        Args:
            role_name: Name of the role (must be in ROLE_REPOSITORIES)
            
        Returns:
            Result dict with status and server path
            
        Raises:
            ValueError: If role_name is not in ROLE_REPOSITORIES or SSH not configured
            Exception: If SSH command fails
        """
        if not self.allow_ssh_install:
            raise ValueError(
                "SSH installation not enabled. Set allow_ssh_install=True and configure SSH credentials."
            )
        
        if role_name not in self.ROLE_REPOSITORIES:
            raise ValueError(
                f"Role {role_name} not in ROLE_REPOSITORIES. "
                f"Available: {list(self.ROLE_REPOSITORIES.keys())}"
            )
        
        repo_info = self.ROLE_REPOSITORIES[role_name]
        if isinstance(repo_info, tuple):
            repo_url, subdirectory = repo_info
        else:
            repo_url = repo_info
            subdirectory = None
        
        server_role_path = f"{self.SERVER_ROLES_PATH}/{role_name}"
        
        # Build SSH command
        ssh_cmd = ["ssh"]
        
        # Add SSH key if provided
        if self.ssh_key_path:
            ssh_cmd.extend(["-i", self.ssh_key_path])
        
        # Add options to avoid host key checking prompts
        ssh_cmd.extend([
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "ConnectTimeout=10",
        ])
        
        # Build remote command
        remote_cmd_parts = [
            f"mkdir -p {self.SERVER_ROLES_PATH}",
            f"cd {self.SERVER_ROLES_PATH}",
        ]
        
        # Check if directory already exists
        if subdirectory:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_dir = f"{self.SERVER_ROLES_PATH}/{repo_name}"
            remote_cmd_parts.append(
                f"if [ ! -d '{clone_dir}' ]; then git clone {repo_url} {repo_name}; fi"
            )
            remote_cmd_parts.append(f"cd {repo_name}")
            remote_cmd_parts.append(f"git pull || true")  # Update if exists
        else:
            remote_cmd_parts.append(
                f"if [ ! -d '{server_role_path}' ]; then git clone {repo_url} {role_name}; else cd {role_name} && git pull; fi"
            )
        
        remote_cmd = " && ".join(remote_cmd_parts)
        
        # Add password authentication if needed (using sshpass)
        if self.ssh_password and not self.ssh_key_path:
            # Use sshpass for password authentication
            ssh_cmd = ["sshpass", "-p", self.ssh_password] + ssh_cmd
        
        ssh_cmd.append(f"{self.ssh_user}@{self.ssh_host}")
        ssh_cmd.append(remote_cmd)
        
        logger.info(f"Cloning {role_name} on Ludus server via SSH: {self.ssh_host}")
        logger.debug(f"SSH command: {' '.join(ssh_cmd[:3])}... {remote_cmd[:100]}...")
        
        try:
            result = subprocess.run(
                ssh_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            logger.info(f"Successfully cloned {role_name} on Ludus server to {server_role_path}")
            
            return {
                "status": "success",
                "role_name": role_name,
                "server_path": server_role_path,
                "message": f"Role {role_name} cloned successfully on Ludus server",
            }
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout cloning {role_name} on Ludus server via SSH")
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else e.stdout if e.stdout else "Unknown error"
            raise Exception(
                f"Failed to clone {role_name} on Ludus server via SSH: {error_output}"
            )
    
    async def clone_role_repository(self, role_name: str) -> Path:
        """Clone a role repository from GitHub.
        
        Handles roles that are in subdirectories of repositories.
        
        Args:
            role_name: Name of the role (must be in ROLE_REPOSITORIES)
            
        Returns:
            Path to the role directory (may be a subdirectory of cloned repo)
            
        Raises:
            ValueError: If role_name is not in ROLE_REPOSITORIES
            Exception: If cloning fails
        """
        if role_name not in self.ROLE_REPOSITORIES:
            raise ValueError(
                f"Role {role_name} not in ROLE_REPOSITORIES. "
                f"Available: {list(self.ROLE_REPOSITORIES.keys())}"
            )
        
        repo_info = self.ROLE_REPOSITORIES[role_name]
        if isinstance(repo_info, tuple):
            repo_url, subdirectory = repo_info
        else:
            # Backward compatibility: treat as string URL
            repo_url = repo_info
            subdirectory = None
        
        # Determine clone directory name (use repo name or role name)
        if subdirectory:
            # For roles in subdirectories, clone to repo name, then point to subdirectory
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_dir = self.roles_cache_dir / repo_name
            role_dir = clone_dir / subdirectory
        else:
            # For standalone roles, clone directly to role name
            clone_dir = self.roles_cache_dir / role_name
            role_dir = clone_dir
        
        # Check if already cloned
        if clone_dir.exists() and (clone_dir / ".git").exists():
            logger.info(f"Repository for {role_name} already cloned at {clone_dir}")
            # Optionally update it
            try:
                subprocess.run(
                    ["git", "pull"],
                    cwd=clone_dir,
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                logger.debug(f"Updated repository for {role_name}")
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout updating repository for {role_name}")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Failed to update repository for {role_name}: {e}")
            
            # Verify subdirectory exists if needed
            if subdirectory and not role_dir.exists():
                raise Exception(
                    f"Role subdirectory {subdirectory} not found in cloned repository {clone_dir}. "
                    f"Expected path: {role_dir}"
                )
            
            return role_dir
        
        # Clone the repository
        logger.info(f"Cloning repository for {role_name} from {repo_url} to {clone_dir}")
        try:
            subprocess.run(
                ["git", "clone", repo_url, str(clone_dir)],
                check=True,
                capture_output=True,
                timeout=120
            )
            logger.info(f"Successfully cloned repository for {role_name} to {clone_dir}")
            
            # Verify subdirectory exists if needed
            if subdirectory:
                if not role_dir.exists():
                    raise Exception(
                        f"Role subdirectory {subdirectory} not found in cloned repository. "
                        f"Expected path: {role_dir}. "
                        f"Available directories: {[d.name for d in clone_dir.iterdir() if d.is_dir()]}"
                    )
                logger.info(f"Role {role_name} is in subdirectory: {role_dir}")
            
            return role_dir
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout cloning repository for {role_name}")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise Exception(f"Failed to clone repository for {role_name}: {error_msg}")
    
    async def install_role_from_directory(self, role_dir: Path, role_name: str | None = None) -> dict[str, Any]:
        """Install an Ansible role from a directory on the Ludus server.
        
        IMPORTANT: The directory path must exist on the Ludus server, not the client.
        Roles should be cloned to /opt/ludus/roles/ on the Ludus server.
        
        Args:
            role_dir: Path to the role directory (on Ludus server, e.g., /opt/ludus/roles/ludus-ad-content)
            role_name: Optional role name (defaults to directory name)
            
        Returns:
            Installation result dict
            
        Raises:
            Exception: If installation fails
        """
        role_name = role_name or role_dir.name
        logger.info(f"Installing role {role_name} from server directory: {role_dir}")
        
        # Use server-side path (absolute path on Ludus server)
        # The API expects paths on the Ludus server, not the client
        server_path = str(role_dir) if str(role_dir).startswith("/") else f"{self.SERVER_ROLES_PATH}/{role_dir}"
        
        config = {
            "action": "install",
            "name": role_name,
            "directory": server_path,
        }
        
        try:
            result = await self.client.install_ansible_role(config)
            logger.info(f"[OK] Successfully installed role {role_name} from directory: {server_path}")
            return result
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"API installation failed for {role_name}: {error_msg}")
            logger.info(f"Role may need to be cloned on Ludus server first:")
            logger.info(f"  cd {self.SERVER_ROLES_PATH}")
            logger.info(f"  git clone {self.ROLE_REPOSITORIES.get(role_name, ('<repository-url>', None))[0]}")
            logger.info(f"  ludus ansible role add -d {server_path}")
            
            # Return a result indicating manual installation is needed
            return {
                "status": "manual_installation_required",
                "role_name": role_name,
                "directory": server_path,
                "command": f"ludus ansible role add -d {server_path}",
                "note": f"Clone repository on Ludus server to {server_path} first, then install"
            }
    
    async def install_role(
        self, role_name: str, role_url: str | None = None, max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Install an Ansible role with retry logic.
        
        If the role is in ROLE_REPOSITORIES, it will be cloned and installed from local directory.
        Otherwise, it will be installed from Ansible Galaxy.

        Args:
            role_name: Name of the role to install
            role_url: Optional URL to install from (overrides repository lookup)
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Installation result dict

        Raises:
            Exception: If all retry attempts fail
        """
        # Check if this role needs to be installed from a directory on the Ludus server
        if role_name in self.ROLE_REPOSITORIES and not role_url:
            logger.info(f"Role {role_name} must be installed from directory on Ludus server")
            # Use server-side path (assumes role is cloned to /opt/ludus/roles/<role-name>)
            server_role_path = Path(f"{self.SERVER_ROLES_PATH}/{role_name}")
            
            # Try to install from server directory
            # Note: The directory must already exist on the Ludus server
            # If it doesn't exist, try SSH installation if enabled
            try:
                result = await self.install_role_from_directory(server_role_path, role_name)
                if result.get("status") == "manual_installation_required":
                    # Directory doesn't exist on server
                    # Try SSH installation if enabled
                    if self.allow_ssh_install:
                        logger.info(f"Attempting to clone {role_name} on Ludus server via SSH...")
                        try:
                            clone_result = await self.clone_role_on_server_via_ssh(role_name)
                            logger.info(f"Successfully cloned {role_name} on server, retrying installation...")
                            # Retry installation now that directory exists
                            result = await self.install_role_from_directory(server_role_path, role_name)
                            if result.get("status") == "manual_installation_required":
                                # Still failed, provide instructions
                                repo_url = self.ROLE_REPOSITORIES[role_name][0]
                                raise Exception(
                                    f"Role {role_name} cloned on server but installation failed. "
                                    f"Try manually: ludus ansible role add -d {self.SERVER_ROLES_PATH}/{role_name}"
                                )
                            return result
                        except Exception as ssh_error:
                            logger.warning(f"SSH installation failed: {ssh_error}")
                            # Fall through to manual instructions
                    
                    # Provide manual installation instructions
                    repo_url = self.ROLE_REPOSITORIES[role_name][0]
                    raise Exception(
                        f"Role {role_name} not found on Ludus server. "
                        f"Clone it first: cd {self.SERVER_ROLES_PATH} && git clone {repo_url} && "
                        f"ludus ansible role add -d {self.SERVER_ROLES_PATH}/{role_name}"
                    )
                return result
            except Exception as e:
                error_msg = str(e)
                # If it's already our formatted error, re-raise it
                if "not found on Ludus server" in error_msg or "Clone it first" in error_msg:
                    raise
                # Otherwise, provide helpful error message
                repo_url = self.ROLE_REPOSITORIES[role_name][0]
                raise Exception(
                    f"Failed to install {role_name} from directory. "
                    f"Ensure it's cloned on Ludus server: cd {self.SERVER_ROLES_PATH} && git clone {repo_url}"
                ) from e
        
        # Standard installation from Ansible Galaxy
        logger.info(f"Installing Ludus role from Ansible Galaxy: {role_name}")

        config = {
            "action": "install",
            "name": role_name,
        }
        if role_url:
            config["url"] = role_url

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(f"Install attempt {attempt + 1}/{max_retries} for role: {role_name}")
                result = await self.client.install_ansible_role(config)
                logger.info(f"Successfully installed role: {role_name}")
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e)
                logger.warning(
                    f"Failed to install role {role_name} (attempt {attempt + 1}/{max_retries}): {error_msg}"
                )

                # Don't retry if it's a 404 (role not found) or similar permanent errors
                if "404" in error_msg or "not found" in error_msg.lower():
                    logger.error(f"Role {role_name} not found in repository. Cannot retry.")
                    raise

                # Wait before retrying (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.debug(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

        # All retries failed
        logger.error(f"Failed to install role {role_name} after {max_retries} attempts")
        raise Exception(
            f"Failed to install role {role_name} after {max_retries} attempts. "
            f"Last error: {last_error}"
        )

    @staticmethod
    def roles_in_config(config: dict[str, Any] | None) -> list[str]:
        """Extract every Ansible role named by a scenario/range config.

        The authoritative list of what a scenario needs is the config itself.
        Deriving it from the scenario key alone missed roles entirely - the
        wireless lab needs ludus.docker, which no key-prefix rule mentioned, so
        deployment failed with "the role 'ludus.docker' does not exist".
        """
        if not isinstance(config, dict):
            return []
        vms = config.get("ludus", [])
        if isinstance(vms, dict):
            vms = vms.get("vms", [])
        found: list[str] = []
        for vm in vms if isinstance(vms, list) else []:
            if not isinstance(vm, dict):
                continue
            for role in vm.get("roles", []) or []:
                if isinstance(role, str):
                    found.append(role)
                elif isinstance(role, dict) and role.get("name"):
                    found.append(role["name"])
        return found

    async def ensure_roles_for_scenario(
        self,
        scenario_key: str,
        auto_install: bool = True,
        siem_type: str = "wazuh",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ensure required roles are installed for a scenario.

        Args:
            scenario_key: Scenario identifier
            auto_install: Install anything missing
            siem_type: SIEM flavour, which pulls in its own roles
            config: The scenario's built config. When given, roles are read from
                it directly - far more reliable than inferring from the key.
        """
        logger.info(f"Checking roles for scenario: {scenario_key} with SIEM: {siem_type}")

        # Roles named by the config always count, whatever the key looks like
        required_roles = list(self.roles_in_config(config))
        if scenario_key.startswith("goad"):
            required_roles.extend(self.REQUIRED_ROLES.get("goad", []))
        elif (scenario_key.startswith("ad-") or 
              scenario_key.startswith("purple-") or 
              scenario_key.startswith("red-vs-blue") or
              scenario_key.startswith("redteam-lab") or
              scenario_key.startswith("blueteam-lab")):
            # Determine AD role set based on scenario level
            if scenario_key.endswith("-intermediate"):
                required_roles.extend(self.REQUIRED_ROLES.get("ad-intermediate", []))
            elif scenario_key.endswith("-advanced"):
                required_roles.extend(self.REQUIRED_ROLES.get("ad-advanced", []))
            else:
                required_roles.extend(self.REQUIRED_ROLES.get("ad", []))
            
            # Check if scenario needs SQL Server (intermediate/advanced red team scenarios)
            if scenario_key.startswith("redteam-lab") and (
                scenario_key.endswith("-intermediate") or scenario_key.endswith("-advanced")
            ):
                required_roles.extend(self.REQUIRED_ROLES.get("sql", []))
        if scenario_key.startswith("web-") or scenario_key in ["dvwa", "owasp-top10"]:
            required_roles.extend(self.REQUIRED_ROLES.get("web", []))
        if scenario_key.startswith("network-") or scenario_key.startswith("wireless"):
            required_roles.extend(self.REQUIRED_ROLES.get("network", []))
        if scenario_key.startswith("purple-") or scenario_key == "red-vs-blue":
            required_roles.extend(self.REQUIRED_ROLES.get("purple-team", []))
        
        # Add SIEM-specific roles
        if siem_type == "wazuh":
            required_roles.extend(self.REQUIRED_ROLES.get("wazuh", []))
        elif siem_type == "splunk":
            required_roles.extend(self.REQUIRED_ROLES.get("splunk", []))
        elif siem_type == "elastic":
            required_roles.extend(self.REQUIRED_ROLES.get("elastic", []))
        elif siem_type == "security-onion":
            required_roles.extend(self.REQUIRED_ROLES.get("security-onion", []))
        
        # Remove duplicates
        required_roles = list(set(required_roles))
        
        if not required_roles:
            logger.info("No specific roles required for this scenario")
            return {"status": "no_roles_required", "roles": []}
        
        results = {
            "status": "checked",
            "required_roles": required_roles,
            "installed": [],
            "missing": [],
            "install_attempted": [],
            "install_failed": [],
        }
        
        for role_name in required_roles:
            is_installed = await self.check_role_installed(role_name)
            if is_installed:
                logger.info(f"[OK] Role {role_name} is already installed")
                results["installed"].append(role_name)
            else:
                logger.warning(f"Role {role_name} is NOT installed")
                results["missing"].append(role_name)
                
                if auto_install:
                    try:
                        logger.info(f"Attempting to install role: {role_name}")
                        install_result = await self.install_role(role_name)
                        results["install_attempted"].append(role_name)
                        
                        # Check if installation was successful
                        if install_result.get("status") == "manual_installation_required":
                            # Directory-based role needs manual setup
                            error_msg = install_result.get("note", "Manual installation required")
                            logger.warning(f"Role {role_name} requires manual setup: {error_msg}")
                            results["install_failed"].append({
                                "role": role_name, 
                                "error": error_msg,
                                "command": install_result.get("command", "")
                            })
                        else:
                            # Verify installation succeeded
                            is_now_installed = await self.check_role_installed(role_name)
                            if is_now_installed:
                                logger.info(f"[OK] Successfully installed role: {role_name}")
                                results["installed"].append(role_name)
                                if role_name in results["missing"]:
                                    results["missing"].remove(role_name)
                            else:
                                logger.warning(f"Role {role_name} installation reported success but not found in installed roles")
                                results["install_failed"].append({
                                    "role": role_name,
                                    "error": "Installation reported success but role not found"
                                })
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Failed to install role {role_name}: {error_msg}")
                        results["install_failed"].append({"role": role_name, "error": error_msg})
        
        if results["missing"] and not auto_install:
            logger.warning(
                f"Missing roles: {results['missing']}. "
                f"Set auto_install=True to install automatically."
            )
        
        return results


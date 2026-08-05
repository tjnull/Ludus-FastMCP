"""Custom template and range builder tools for Ludus MCP server.

This module provides tools for users to create custom templates and ranges
from the provided scenarios, allowing full customization and flexibility.
"""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.template_builder import TemplateBuilder
from ludus_mcp.server.handlers.scenarios import ScenarioHandler
from ludus_mcp.server.handlers.range_builder import RangeBuilderHandler
from ludus_mcp.scenarios.base import BaseScenarioBuilder
from ludus_mcp.scenarios.skeleton_templates import (
    VMSkeletons,
    RangeSkeletons,
    YAML_EXAMPLES,
    get_yaml_example as _get_yaml_example,
    list_yaml_examples,
)
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


def create_custom_builder_tools(client: LudusAPIClient) -> FastMCP:
    """Create custom template and range builder tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with custom builder tools registered
    """
    mcp = FastMCP("Custom Template & Range Builder")
    registry = LazyHandlerRegistry(client)

    # ==================== CUSTOM TEMPLATE CREATION ====================

    @mcp.tool()
    async def create_custom_os_template(
        name: str,
        os_type: str | None = None,
        os_version: str | None = None,
        iso_url: str | None = None,
        iso_checksum: str | None = None,
        iso_checksum_type: str = "sha256",
        packages: list[str] | None = None,
        ansible_roles: list[str] | None = None,
        description: str | None = None,
        disk_size: str = "40G",
        memory: int = 4096,
        cores: int = 2,
        ensure_template_roles: bool = True,
        auto_detect_os: bool = True,
    ) -> dict:
        """Create a custom OS template with specific packages and configuration.

        This tool allows you to create custom Ludus templates from ANY operating system
        by providing an ISO URL. The OS type can be auto-detected from the ISO URL/filename,
        or explicitly specified. Supports Linux, Windows, BSD, macOS, and any other OS.

        Args:
            name: Template name (e.g., "ubuntu-22.04-pentesting")
            os_type: OS type ("linux", "windows", "bsd", "macos") - auto-detected if None
            os_version: OS version (e.g., "22.04", "2022", "11") - used for default ISO lookup
            iso_url: Custom ISO URL (required if os_version not in defaults, supports ANY ISO)
            iso_checksum: Optional ISO checksum for verification (sha256)
            iso_checksum_type: Checksum type (default: "sha256")
            packages: List of packages to install (e.g., ["docker.io", "nginx", "postgresql"])
            ansible_roles: List of Ansible roles to apply (e.g., ["geerlingguy.docker"])
            description: Template description
            disk_size: Disk size (default: "40G")
            memory: Memory in MB (default: 4096)
            cores: CPU cores (default: 2)
            ensure_template_roles: Automatically install template roles (CommandoVM, FlareVM, REMnux) if needed
            auto_detect_os: Auto-detect OS type from ISO URL (default: True)

        Returns:
            Template creation result with file paths and instructions

        Example:
            # Create a custom Ubuntu pentesting template
            result = await create_custom_os_template(
                name="ubuntu-22.04-pentesting",
                os_type="linux",
                os_version="22.04",
                packages=["nmap", "metasploit-framework", "burpsuite"],
                description="Custom Ubuntu 22.04 with pentesting tools"
            )
            
            # Create template from ANY ISO (OS auto-detected)
            result = await create_custom_os_template(
                name="custom-os",
                iso_url="https://example.com/custom-linux.iso",
                iso_checksum="abc123...",
                description="Custom OS from ISO - OS type auto-detected"
            )
            
            # Create template for any operating system
            result = await create_custom_os_template(
                name="arch-linux",
                iso_url="https://archlinux.org/iso/latest/archlinux-x86_64.iso",
                description="Arch Linux template"
            )
        """
        # Ensure template roles are installed if requested
        if ensure_template_roles:
            from ludus_mcp.scenarios.role_manager import RoleManager
            role_manager = RoleManager(client)
            template_roles = role_manager.REQUIRED_ROLES.get("template", [])
            for role in template_roles:
                try:
                    if not await role_manager.check_role_installed(role):
                        logger.info(f"Installing template role: {role}")
                        await role_manager.install_role(role)
                except Exception as e:
                    logger.warning(f"Could not install template role {role}: {e}")
        
        builder = TemplateBuilder()

        result = builder.create_template(
            name=name,
            os_type=os_type,
            os_version=os_version,
            iso_url=iso_url,
            iso_checksum=iso_checksum,
            iso_checksum_type=iso_checksum_type,
            packages=packages or [],
            ansible_roles=ansible_roles,
            description=description,
            disk_size=disk_size,
            memory=memory,
            cores=cores,
            auto_detect_os=auto_detect_os,
        )

        return {
            "status": "success",
            "template_name": result["name"],
            "template_directory": result["directory"],
            "os_type": result["os_type"],
            "os_version": result["os_version"],
            "files_created": result["files_created"],
            "next_steps": [
                f"1. Review template files in: {result['directory']}",
                f"2. Add template to Ludus: ludus templates add --directory {result['directory']}",
                f"3. Build template: ludus templates build --template {result['name']}",
                f"4. Use in range config: template: {result['name']}",
            ],
        }
    
    @mcp.tool()
    async def create_kali_weekly_template(
        name: str = "kali-weekly-latest",
        packages: list[str] | None = None,
        ansible_roles: list[str] | None = None,
        description: str | None = None,
        disk_size: str = "40G",
        memory: int = 4096,
        cores: int = 2,
    ) -> dict:
        """Create a Kali Linux weekly template with automatic latest ISO detection.
        
        Automatically fetches the latest Kali Linux weekly ISO and checksum from
        https://cdimage.kali.org/kali-weekly/. The ISO URL and checksum change
        weekly, so this tool always uses the most recent version.
        
        Args:
            name: Template name (default: "kali-weekly-latest")
            packages: Additional packages to install (e.g., ["metasploit-framework", "burpsuite"])
            ansible_roles: Ansible roles to apply
            description: Template description
            disk_size: Disk size (default: "40G")
            memory: Memory in MB (default: 4096)
            cores: CPU cores (default: 2)
        
        Returns:
            Template creation result with ISO information and instructions
        
        Example:
            # Create latest Kali weekly template
            result = await create_kali_weekly_template(
                name="kali-weekly-pentesting",
                packages=["nmap", "metasploit-framework", "burpsuite"],
                description="Latest Kali weekly with pentesting tools"
            )
        """
        builder = TemplateBuilder()
        
        try:
            result = builder.create_kali_weekly_template(
                name=name,
                packages=packages or [],
                ansible_roles=ansible_roles,
                description=description,
                disk_size=disk_size,
                memory=memory,
                cores=cores,
            )
            
            kali_info = result.get("kali_iso_info", {})
            
            return {
                "status": "success",
                "template_name": result["name"],
                "template_directory": result["directory"],
                "kali_info": {
                    "filename": kali_info.get("iso_filename", "unknown"),
                    "year": kali_info.get("year", "unknown"),
                    "week": kali_info.get("week", "unknown"),
                    "iso_url": kali_info.get("iso_url", "unknown"),
                    "checksum": kali_info.get("iso_checksum", "unknown")[:32] + "...",
                },
                "files_created": result["files_created"],
                "next_steps": [
                    f"1. Review template files in: {result['directory']}",
                    f"2. Add template to Ludus: ludus templates add --directory {result['directory']}",
                    f"3. Build template: ludus templates build --template {result['name']}",
                    f"4. Use in range config: template: {result['name']}",
                ],
                "note": f"Using Kali Linux Weekly {kali_info.get('year', '?')} Week {kali_info.get('week', '?')}",
            }
        except Exception as e:
            logger.error(f"Failed to create Kali weekly template: {e}")
            return {
                "status": "error",
                "error": str(e),
                "suggestion": "Check network connectivity and verify https://cdimage.kali.org/kali-weekly/ is accessible",
            }
    
    @mcp.tool()
    async def get_common_iso_urls() -> dict:
        """Get common ISO download URLs for popular operating systems.
        
        Returns a reference of ISO download URLs for various operating systems
        that can be used with create_custom_os_template.
        
        Returns:
            Dictionary of OS names to ISO download information
        
        Example:
            # Get common ISO URLs
            isos = await get_common_iso_urls()
            # Use one of the URLs
            result = await create_custom_os_template(
                name="arch-linux",
                iso_url=isos["arch_linux"]["url"],
                description="Arch Linux template"
            )
        """
        return {
            "ubuntu_22_04": {
                "name": "Ubuntu 22.04 LTS",
                "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso",
                "os_type": "linux",
                "checksum_type": "sha256",
            },
            "ubuntu_20_04": {
                "name": "Ubuntu 20.04 LTS",
                "url": "https://releases.ubuntu.com/20.04/ubuntu-20.04.6-live-server-amd64.iso",
                "os_type": "linux",
                "checksum_type": "sha256",
            },
            "debian_12": {
                "name": "Debian 12",
                "url": "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.4.0-amd64-netinst.iso",
                "os_type": "linux",
                "checksum_type": "sha256",
            },
            "rocky_9": {
                "name": "Rocky Linux 9",
                "url": "https://download.rockylinux.org/pub/rocky/9/isos/x86_64/Rocky-9.3-x86_64-minimal.iso",
                "os_type": "linux",
                "checksum_type": "sha256",
            },
            "arch_linux": {
                "name": "Arch Linux",
                "url": "https://archlinux.org/iso/latest/archlinux-x86_64.iso",
                "os_type": "linux",
                "checksum_type": "sha256",
                "note": "URL always points to latest version",
            },
            "kali_linux": {
                "name": "Kali Linux",
                "url": "https://cdimage.kali.org/kali-2024.1/kali-linux-2024.1-live-amd64.iso",
                "os_type": "linux",
                "checksum_type": "sha256",
                "note": "Use create_kali_weekly_template() for latest weekly builds",
            },
            "freebsd_14": {
                "name": "FreeBSD 14.0",
                "url": "https://download.freebsd.org/releases/amd64/amd64/ISO-IMAGES/14.0/FreeBSD-14.0-RELEASE-amd64-disc1.iso",
                "os_type": "bsd",
                "checksum_type": "sha256",
            },
            "windows_server_2022": {
                "name": "Windows Server 2022",
                "url": "https://software-download.microsoft.com/download/sg/20348.169.210806-2348.fe_release_svc_refresh_SERVER_EVAL_x64FRE_en-us.iso",
                "os_type": "windows",
                "checksum_type": "sha256",
                "note": "Evaluation version - requires Microsoft account",
            },
            "windows_11": {
                "name": "Windows 11",
                "url": "https://software-download.microsoft.com/download/sg/22000.194.210913-1125.co_release_svc_refresh_CLIENTENTERPRISEEVAL_OEMRET_x64FRE_en-us.iso",
                "os_type": "windows",
                "checksum_type": "sha256",
                "note": "Evaluation version - requires Microsoft account",
            },
            "note": "These are example URLs. Always verify checksums and use official sources. For custom ISOs, provide your own URL and checksum.",
        }

    @mcp.tool()
    async def build_container_based_template(
        name: str,
        base_os: str,
        containers: list[dict[str, Any]],
        description: str | None = None,
    ) -> dict:
        """Build a custom container-based template for applications.

        This tool creates templates specifically designed to run Docker containers,
        perfect for deploying applications like Splunk, Wazuh, Grafana, etc.

        Args:
            name: Template name (e.g., "ubuntu-splunk-server")
            base_os: Base OS (e.g., "ubuntu-22.04", "debian-12", "rocky-9")
            containers: List of container configurations with image, ports, volumes, env
            description: Template description

        Returns:
            Template creation result with docker-compose configuration

        Example:
            # Create a Splunk container template
            result = await create_container_template(
                name="ubuntu-splunk-server",
                base_os="ubuntu-22.04",
                containers=[{
                    "image": "splunk/splunk:latest",
                    "ports": ["8000:8000", "8088:8088", "9997:9997"],
                    "environment": {
                        "SPLUNK_START_ARGS": "--accept-license",
                        "SPLUNK_PASSWORD": "changeme123!"
                    }
                }],
                description="Ubuntu 22.04 with Splunk container"
            )
        """
        builder = TemplateBuilder()

        result = builder.create_container_template(
            name=name,
            base_os=base_os,
            containers=containers,
            description=description,
        )

        return {
            "status": "success",
            "template_name": result["name"],
            "template_directory": result["directory"],
            "base_os": base_os,
            "containers_configured": len(containers),
            "has_docker_compose": True,
            "files_created": result["files_created"],
            "next_steps": [
                f"1. Review template files in: {result['directory']}",
                "2. Check docker-compose.yml for container configuration",
                f"3. Add template to Ludus: ludus templates add --directory {result['directory']}",
                f"4. Build template: ludus templates build --template {result['name']}",
            ],
        }

    @mcp.tool()
    async def get_common_container_configs() -> dict:
        """Get pre-configured container definitions for common applications.

        Returns a dictionary of common application containers (Splunk, Wazuh, ELK,
        Nginx, PostgreSQL, Redis, Grafana) that can be used with create_container_template.

        Returns:
            Dictionary of application name to container configuration

        Example:
            # Get all common container configs
            configs = await get_common_container_configs()

            # Use Splunk config to create template
            splunk_config = configs["splunk"]
            result = await create_container_template(
                name="ubuntu-splunk",
                base_os="ubuntu-22.04",
                containers=[splunk_config]
            )
        """
        builder = TemplateBuilder()
        configs = builder.get_common_container_configs()

        return {
            "available_applications": list(configs.keys()),
            "configurations": configs,
            "usage_example": {
                "description": "Use these configs with create_container_template",
                "example": "create_container_template(name='my-app', base_os='ubuntu-22.04', containers=[configs['splunk']])",
            },
        }

    # ==================== CUSTOM RANGE CREATION FROM SCENARIOS ====================

    @mcp.tool()
    async def create_custom_range_from_scenario(
        scenario_key: str,
        customizations: dict[str, Any],
        siem_type: str = "wazuh",
    ) -> dict:
        """Create a custom range configuration based on an existing scenario.

        This tool takes an existing scenario and allows you to customize it with
        your own modifications (add/remove VMs, change specs, modify network rules).

        Args:
            scenario_key: Base scenario to start from (e.g., "ad-basic", "web-basic", "kerberoasting")
            customizations: Dictionary of customizations to apply
            siem_type: SIEM type to use ("wazuh", "splunk", "elastic", "security-onion", "none")

        Returns:
            Customized range configuration ready for deployment

        Customization options:
            - add_vms: List of VM configurations to add
            - remove_vms: List of VM names to remove
            - modify_vms: Dictionary of VM name to modifications
            - add_network_rules: List of network rules to add
            - modify_range_settings: Range-level settings to modify

        Example:
            # Start with basic AD scenario and customize
            customizations = {
                "add_vms": [{
                    "vm_name": "my-web-server",
                    "hostname": "webserver01",
                    "template": "ubuntu-22.04-template",
                    "vlan": 10,
                    "ip_last_octet": 50,
                    "ram_gb": 4,
                    "cpus": 2
                }],
                "modify_vms": {
                    "ad-dc-win2022-server-x64": {
                        "ram_gb": 16,  # Increase RAM
                        "cpus": 8      # Increase CPUs
                    }
                },
                "add_network_rules": [{
                    "name": "Allow web traffic",
                    "vlan_src": 99,
                    "vlan_dst": 10,
                    "protocol": "tcp",
                    "ports": 80,
                    "action": "ACCEPT"
                }]
            }
            result = await create_custom_range_from_scenario(
                scenario_key="ad-basic",
                customizations=customizations,
                siem_type="wazuh"
            )
        """
        handler = registry.get_handler("scenario", ScenarioHandler)

        # Get base scenario configuration
        base_config = await handler.get_scenario_config(scenario_key, siem_type)

        # Apply customizations
        custom_config = _apply_customizations(base_config, customizations)

        return {
            "status": "success",
            "base_scenario": scenario_key,
            "siem_type": siem_type,
            "configuration": custom_config,
            "customizations_applied": {
                "vms_added": len(customizations.get("add_vms", [])),
                "vms_removed": len(customizations.get("remove_vms", [])),
                "vms_modified": len(customizations.get("modify_vms", {})),
                "network_rules_added": len(customizations.get("add_network_rules", [])),
            },
            "vm_count": len(custom_config.get("ludus", [])),
            "next_steps": [
                "1. Review the configuration to ensure it meets your needs",
                "2. Save configuration to YAML file if desired",
                "3. Deploy with: ludus.deploy_range(config=configuration)",
            ],
        }

    @mcp.tool()
    async def build_range_from_scratch(
        vms: list[dict[str, Any]],
        network_rules: list[dict[str, Any]] | None = None,
        inter_vlan_default: str = "REJECT",
        include_siem: bool = True,
        siem_type: str = "wazuh",
    ) -> dict:
        """Build a completely custom range configuration from scratch.

        This tool allows you to create a range configuration with full control
        over every VM and network rule, not based on any existing scenario.

        Args:
            vms: List of VM configurations (each with vm_name, hostname, template, vlan, ip_last_octet, ram_gb, cpus)
            network_rules: Optional list of network rules
            inter_vlan_default: Default inter-VLAN policy ("REJECT" or "ACCEPT")
            include_siem: Whether to automatically add a SIEM server
            siem_type: SIEM type if include_siem is True

        Returns:
            Complete range configuration ready for deployment

        Example:
            # Build a custom 3-VM pentesting lab from scratch
            vms = [
                {
                    "vm_name": "target-web-server",
                    "hostname": "web01",
                    "template": "ubuntu-22.04-template",
                    "vlan": 10,
                    "ip_last_octet": 10,
                    "ram_gb": 4,
                    "cpus": 2
                },
                {
                    "vm_name": "target-database",
                    "hostname": "db01",
                    "template": "ubuntu-22.04-template",
                    "vlan": 10,
                    "ip_last_octet": 11,
                    "ram_gb": 8,
                    "cpus": 4
                },
                {
                    "vm_name": "attacker-kali",
                    "hostname": "kali",
                    "template": "kali-x64-desktop-template",
                    "vlan": 99,
                    "ip_last_octet": 1,
                    "ram_gb": 8,
                    "cpus": 4
                }
            ]

            network_rules = [
                {
                    "name": "Allow attacker to targets",
                    "vlan_src": 99,
                    "vlan_dst": 10,
                    "protocol": "all",
                    "ports": "all",
                    "action": "ACCEPT"
                }
            ]

            result = await build_range_from_scratch(
                vms=vms,
                network_rules=network_rules,
                include_siem=True,
                siem_type="wazuh"
            )
        """
        # Create builder
        builder = BaseScenarioBuilder(siem_type=siem_type)

        # Add all VMs
        for vm_config in vms:
            builder.add_vm(**vm_config)

        # Add network rules
        if network_rules:
            for rule in network_rules:
                builder.add_network_rule(**rule)

        # Set inter-VLAN default
        builder.config["network"]["inter_vlan_default"] = inter_vlan_default

        # Add SIEM if requested
        if include_siem and siem_type != "none":
            builder.add_siem_server(vlan=10, ip_last_octet=100)
            builder.add_siem_agents_to_all_vms()

        config = builder.to_dict()

        return {
            "status": "success",
            "configuration": config,
            "vm_count": len(vms),
            "network_rules_count": len(network_rules or []),
            "has_siem": include_siem and siem_type != "none",
            "siem_type": siem_type if include_siem else "none",
            "next_steps": [
                "1. Review the configuration",
                "2. Save to YAML file if desired",
                "3. Deploy with: ludus.deploy_range(config=configuration)",
            ],
        }

    @mcp.tool()
    async def export_range_config_to_yaml(
        config: dict[str, Any],
        filename: str | None = None,
        include_full_content: bool = True,
    ) -> dict:
        """Export a range configuration to a YAML file for download.

        This tool exports range configurations to YAML format that users can download
        and use with Ludus. The YAML content is provided in the response for easy
        copying or downloading through the chat interface.

        Args:
            config: Range configuration dictionary
            filename: Optional filename (defaults to /tmp/ludus-range-config.yml)
            include_full_content: Whether to include full YAML content in response (default: True)

        Returns:
            File path, YAML content, and download instructions

        Example:
            # Export custom config to file with full content
            result = await export_range_config_to_yaml(
                config=my_config,
                filename="/tmp/my-custom-range.yml",
                include_full_content=True
            )

            # The result includes the full YAML content that users can copy/download
        """
        import yaml
        from pathlib import Path

        if filename is None:
            filename = "/tmp/ludus-range-config.yml"

        # Convert to YAML
        yaml_str = "# yaml-language-server: $schema=https://docs.ludus.cloud/schemas/range-config.json\n\n"
        yaml_str += yaml.dump(config, default_flow_style=False, sort_keys=False)

        # Write to file
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(yaml_str)

        response = {
            "status": "success",
            "file_path": str(file_path),
            "file_size_bytes": len(yaml_str),
            "vm_count": len(config.get("ludus", [])),
            "network_rules_count": len(config.get("network", {}).get("rules", [])),
        }

        # Include full YAML content if requested (for download/copy)
        if include_full_content:
            response["yaml_content"] = yaml_str
            response["download_instructions"] = [
                "1. Copy the YAML content from the 'yaml_content' field below",
                "2. Save it to a file named 'range-config.yml' on your local machine",
                f"3. Or retrieve it from the server at: {file_path}",
                "4. Deploy with: ludus range config set -f range-config.yml",
                "5. Then deploy: ludus range deploy",
            ]
        else:
            response["yaml_preview"] = yaml_str[:500] + "..." if len(yaml_str) > 500 else yaml_str
            response["note"] = f"Full content written to {file_path}"

        return response

    @mcp.tool()
    async def get_current_range_config_for_download(
        user_id: str | None = None,
        filename: str | None = None,
    ) -> dict:
        """Get the current range configuration and prepare it for download.

        This tool retrieves your currently deployed range configuration from Ludus
        and provides it in YAML format for download. Users can then save this
        configuration file and modify/redeploy it as needed.

        Args:
            user_id: Optional user ID (admin only - for getting other users' configs)
            filename: Optional filename to save to (defaults to /tmp/current-range-config.yml)

        Returns:
            Current range configuration in YAML format ready for download

        Example:
            # Get your current range config for download
            result = await get_current_range_config_for_download()

            # The YAML content will be in result["yaml_content"]
            # Users can copy it and save to a local file

        Use Cases:
            - Backup your current range configuration
            - Download config to modify and redeploy later
            - Share your range configuration with team members
            - Version control your range configurations
            - Clone your current range to make variations
        """
        # Get current range configuration from Ludus API
        config = await client.get_range_config(user_id)

        # Export to YAML format with full content
        result = await export_range_config_to_yaml(
            config=config,
            filename=filename or "/tmp/current-range-config.yml",
            include_full_content=True,
        )

        # Add context-specific information
        result["source"] = "current_deployed_range"
        result["user_id"] = user_id or "current_user"
        result["usage_instructions"] = [
            "This is your currently deployed range configuration.",
            "You can:",
            "  1. Save the YAML content to a file for backup",
            "  2. Modify it and redeploy with: ludus range config set -f <file>",
            "  3. Share it with team members",
            "  4. Use it as a template for similar ranges",
        ]

        return result

    @mcp.tool()
    async def clone_and_modify_scenario(
        scenario_key: str,
        modifications: dict[str, Any],
        new_name: str,
        siem_type: str = "wazuh",
    ) -> dict:
        """Clone an existing scenario and modify it to create a new custom scenario.

        This is useful for creating variations of existing scenarios (e.g., "ad-basic"
        with more workstations, or "web-basic" with different applications).

        Args:
            scenario_key: Scenario to clone (e.g., "ad-basic", "kerberoasting")
            modifications: Modifications to apply (same as create_custom_range_from_scenario)
            new_name: Name for the new custom scenario
            siem_type: SIEM type to use

        Returns:
            New scenario configuration with modifications

        Example:
            # Clone "ad-basic" and add more workstations
            modifications = {
                "add_vms": [
                    {
                        "vm_name": "win11-workstation-3",
                        "hostname": "WIN11-03",
                        "template": "win11-22h2-x64-enterprise-template",
                        "vlan": 10,
                        "ip_last_octet": 23,
                        "ram_gb": 8,
                        "cpus": 4,
                        "domain": {"fqdn": "ludus.domain", "role": "member"}
                    },
                    {
                        "vm_name": "win11-workstation-4",
                        "hostname": "WIN11-04",
                        "template": "win11-22h2-x64-enterprise-template",
                        "vlan": 10,
                        "ip_last_octet": 24,
                        "ram_gb": 8,
                        "cpus": 4,
                        "domain": {"fqdn": "ludus.domain", "role": "member"}
                    }
                ]
            }

            result = await clone_and_modify_scenario(
                scenario_key="ad-basic",
                modifications=modifications,
                new_name="ad-basic-extended",
                siem_type="wazuh"
            )
        """
        handler = registry.get_handler("scenario", ScenarioHandler)

        # Get base scenario
        base_config = await handler.get_scenario_config(scenario_key, siem_type)

        # Apply modifications
        custom_config = _apply_customizations(base_config, modifications)

        return {
            "status": "success",
            "base_scenario": scenario_key,
            "new_scenario_name": new_name,
            "siem_type": siem_type,
            "configuration": custom_config,
            "vm_count": len(custom_config.get("ludus", [])),
            "modifications_applied": {
                "vms_added": len(modifications.get("add_vms", [])),
                "vms_removed": len(modifications.get("remove_vms", [])),
                "vms_modified": len(modifications.get("modify_vms", {})),
            },
            "next_steps": [
                "1. Review configuration",
                "2. Export to YAML with export_range_config_to_yaml",
                "3. Deploy with ludus.deploy_range(config=configuration)",
            ],
        }

    # ==================== BUILD RANGE FROM DESCRIPTION ====================

    @mcp.tool()
    async def build_range_from_description(
        description: str,
        siem_type: str = "wazuh",
        resource_profile: str = "recommended",
        include_siem: bool = True,
    ) -> dict:
        """Build a custom range configuration from a natural language description.

        This tool intelligently parses your description and automatically builds
        a complete range configuration with appropriate VMs, network rules, and SIEM.

        Args:
            description: Natural language description of the desired range/scenario
            siem_type: SIEM type to include (wazuh, splunk, elastic, security-onion, none)
            resource_profile: Resource allocation profile (minimal, recommended, maximum)
            include_siem: Whether to include SIEM monitoring

        Returns:
            Complete range configuration ready for deployment

        Examples:
            # Simple AD lab
            "Create an Active Directory lab with 2 workstations and a file server"

            # Red team lab
            "Build a red team lab with a domain controller, 3 workstations, SQL server, and Kali attacker"

            # Web application lab
            "Create a web application testing lab with a web server, database, and Kali attacker"

            # Complex enterprise
            "Build an enterprise environment with AD domain corp.local, 5 workstations, file server, Exchange server, and Wazuh monitoring"

        The tool automatically:
            - Detects AD/domain requirements and adds domain controller
            - Adds appropriate number of workstations
            - Adds servers based on keywords (file server, SQL, web, Exchange)
            - Adds Kali attacker if mentioned
            - Configures network rules for attacker access
            - Adds SIEM monitoring if requested
        """
        handler = RangeBuilderHandler(client)
        result = await handler.build_range_from_description(
            description, siem_type, resource_profile, include_siem
        )
        return format_tool_response(result)

    # ==================== SKELETON TEMPLATE TOOLS ====================

    @mcp.tool()
    async def list_vm_skeletons() -> dict:
        """List all available VM skeleton templates.

        Returns a dictionary of VM skeleton names and their descriptions.
        These skeletons can be used as starting points for building custom VMs.

        Categories include:
        - Domain Controllers (dc-2022, dc-2019, secondary-dc)
        - Workstations (ws-win11, ws-win10)
        - Windows Servers (file-server, sql-server, exchange, web-iis, ca)
        - Linux Servers (ubuntu, debian, rocky, docker)
        - Attacker VMs (kali, parrot, commando)
        - SIEM/Monitoring (wazuh, splunk, elastic, security-onion)
        - Vulnerable Apps (dvwa, juice-shop, metasploitable, vulnhub)

        Returns:
            Dictionary with skeleton names as keys and descriptions as values

        Example:
            skeletons = await list_vm_skeletons()
            # Returns: {"dc-2022": "Windows Server 2022 Domain Controller", ...}
        """
        return {
            "status": "success",
            "skeletons": VMSkeletons.list_skeletons(),
            "usage": "Use get_vm_skeleton(name) to retrieve a specific skeleton configuration",
        }

    @mcp.tool()
    async def get_vm_skeleton(
        name: str,
        customizations: dict[str, Any] | None = None,
    ) -> dict:
        """Get a specific VM skeleton template configuration.

        Retrieves a pre-configured VM skeleton that can be used directly in
        a range configuration or customized further.

        Args:
            name: Skeleton name (e.g., "dc-2022", "kali", "wazuh")
            customizations: Optional dict of fields to override (e.g., {"hostname": "mydc", "ram_gb": 8})

        Returns:
            Complete VM configuration dictionary ready for use

        Available skeletons:
            - dc-2022, dc-2019, secondary-dc: Domain controllers
            - ws-win11, ws-win10: Windows workstations
            - file-server, sql-server, exchange, web-iis, ca: Windows servers
            - ubuntu, debian, rocky, docker: Linux servers
            - kali, parrot, commando: Attacker VMs
            - wazuh, splunk, elastic, security-onion: SIEM systems
            - dvwa, juice-shop, metasploitable, vulnhub: Vulnerable apps

        Example:
            # Get a Kali attacker skeleton
            skeleton = await get_vm_skeleton("kali")

            # Get a DC with custom settings
            skeleton = await get_vm_skeleton("dc-2022", {
                "hostname": "mydc01",
                "domain": {"fqdn": "corp.local", "role": "primary_dc"},
                "ram_gb": 8
            })
        """
        try:
            skeleton = VMSkeletons.get_skeleton(name)

            # Apply customizations if provided
            if customizations:
                for key, value in customizations.items():
                    if isinstance(value, dict) and key in skeleton and isinstance(skeleton[key], dict):
                        # Merge nested dicts
                        skeleton[key].update(value)
                    else:
                        skeleton[key] = value

            return {
                "status": "success",
                "skeleton_name": name,
                "configuration": skeleton,
                "usage": "Add this to your ludus configuration array, or use build_range_from_scratch()",
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e),
                "available_skeletons": list(VMSkeletons.list_skeletons().keys()),
            }

    @mcp.tool()
    async def list_range_skeletons() -> dict:
        """List all available range skeleton templates.

        Returns a dictionary of complete range configurations for common scenarios.
        These provide fully-configured lab environments ready for deployment.

        Available range skeletons:
        - basic-ad: Basic AD lab (1 DC, workstations, optional attacker/SIEM)
        - enterprise-ad: Enterprise AD with CA, servers, multiple workstations
        - red-team: Red team training with DMZ, AD, and network segmentation
        - soc-training: SOC analyst training with SIEM and monitored endpoints
        - web-pentest: Web app pentest with DVWA, Juice Shop, WebGoat
        - malware-analysis: Isolated malware RE lab with FlareVM and REMnux

        Returns:
            Dictionary with skeleton names as keys and descriptions as values

        Example:
            ranges = await list_range_skeletons()
            # Returns: {"basic-ad": "Basic AD lab...", ...}
        """
        return {
            "status": "success",
            "skeletons": RangeSkeletons.list_skeletons(),
            "usage": "Use get_range_skeleton(name) to retrieve a complete range configuration",
        }

    @mcp.tool()
    async def get_range_skeleton(
        name: str,
        domain: str | None = None,
        workstations: int | None = None,
        include_attacker: bool = True,
        include_siem: bool = True,
        siem_type: str = "wazuh",
    ) -> dict:
        """Get a complete range skeleton configuration.

        Retrieves a fully-configured range skeleton with all VMs and network rules.
        Some skeletons support additional customization parameters.

        Args:
            name: Skeleton name (e.g., "basic-ad", "enterprise-ad", "red-team")
            domain: Custom domain name (for AD labs, default: "yourcompany.local")
            workstations: Number of workstations (for basic-ad, default: 2)
            include_attacker: Include Kali attacker VM (default: True)
            include_siem: Include SIEM monitoring (default: True)
            siem_type: SIEM type: "wazuh", "splunk", "elastic" (default: "wazuh")

        Returns:
            Complete range configuration with VMs and network rules

        Available skeletons:
            - basic-ad: Customizable with domain, workstations, attacker, siem
            - enterprise-ad: Full enterprise with CA, file server, SQL, exchange
            - red-team: DMZ + internal AD for red team exercises
            - soc-training: Monitored endpoints for SOC training
            - web-pentest: DVWA, Juice Shop, WebGoat
            - malware-analysis: Isolated RE lab

        Example:
            # Get a basic AD lab
            config = await get_range_skeleton("basic-ad")

            # Get a customized AD lab
            config = await get_range_skeleton(
                "basic-ad",
                domain="corp.local",
                workstations=4,
                siem_type="splunk"
            )
        """
        try:
            # Build kwargs based on skeleton type
            kwargs = {}

            if name == "basic-ad":
                if domain:
                    kwargs["domain"] = domain
                if workstations is not None:
                    kwargs["workstations"] = workstations
                kwargs["include_attacker"] = include_attacker
                kwargs["include_siem"] = include_siem
                kwargs["siem_type"] = siem_type
            elif name == "enterprise-ad":
                if domain:
                    kwargs["domain"] = domain
            elif name == "soc-training":
                kwargs["siem_type"] = siem_type

            skeleton = RangeSkeletons.get_skeleton(name, **kwargs)

            return {
                "status": "success",
                "skeleton_name": name,
                "configuration": skeleton,
                "vm_count": len(skeleton.get("ludus", [])),
                "network_rules_count": len(skeleton.get("network_rules", [])),
                "next_steps": [
                    "1. Review the configuration",
                    "2. Customize domain names, IPs, or resources as needed",
                    "3. Export to YAML with export_range_config_to_yaml()",
                    "4. Deploy with ludus range config set -f <file> && ludus range deploy",
                ],
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e),
                "available_skeletons": list(RangeSkeletons.list_skeletons().keys()),
            }

    @mcp.tool()
    async def list_yaml_examples() -> dict:
        """List all available YAML configuration examples.

        Returns ready-to-use YAML configuration examples that can be
        directly saved to a file and deployed with Ludus.

        Available examples:
        - basic_ad: Basic AD lab with DC, workstations, and attacker
        - with_siem: AD lab with Wazuh SIEM for blue team training
        - web_app_lab: Web application security testing lab

        Returns:
            Dictionary with example names and descriptions

        Example:
            examples = await list_yaml_examples()
            # Then use get_yaml_example("basic_ad") to get the YAML content
        """
        from ludus_mcp.scenarios.skeleton_templates import list_yaml_examples as _list_yaml_examples
        return {
            "status": "success",
            "examples": _list_yaml_examples(),
            "usage": "Use get_yaml_example(name) to retrieve the YAML content",
        }

    @mcp.tool()
    async def get_yaml_example(name: str) -> dict:
        """Get a ready-to-use YAML configuration example.

        Returns the complete YAML content for a specific example configuration.
        The YAML can be saved directly to a file and deployed with Ludus.

        Args:
            name: Example name ("basic_ad", "with_siem", "web_app_lab")

        Returns:
            YAML content string ready to save to a file

        Available examples:
            - basic_ad: Basic AD lab with DC, workstations, and Kali attacker
            - with_siem: AD lab with Wazuh SIEM for blue team training
            - web_app_lab: Web application security testing with DVWA

        Example:
            result = await get_yaml_example("basic_ad")
            # result["yaml_content"] contains the full YAML configuration
            # Save to file and deploy:
            #   ludus range config set -f config.yml
            #   ludus range deploy
        """
        try:
            # NB: the MCP tool below is also called get_yaml_example and
            # shadows the import, so calling it unaliased returned an
            # un-awaited coroutine and the tool failed output validation.
            yaml_content = _get_yaml_example(name)
            return {
                "status": "success",
                "example_name": name,
                "yaml_content": yaml_content,
                "instructions": [
                    "1. Copy the YAML content to a file (e.g., range-config.yml)",
                    "2. Customize domain names, IPs, or templates as needed",
                    "3. Deploy: ludus range config set -f range-config.yml",
                    "4. Then: ludus range deploy",
                ],
            }
        except ValueError as e:
            from ludus_mcp.scenarios.skeleton_templates import list_yaml_examples as _list_yaml_examples
            return {
                "status": "error",
                "error": str(e),
                "available_examples": list(_list_yaml_examples().keys()),
            }

    @mcp.tool()
    async def build_range_from_skeleton(
        skeleton_name: str,
        add_vms: list[str] | None = None,
        remove_vms: list[str] | None = None,
        domain: str | None = None,
        siem_type: str = "wazuh",
        include_siem: bool = True,
        include_attacker: bool = True,
    ) -> dict:
        """Build a complete range configuration starting from a skeleton.

        Combines the power of skeleton templates with custom modifications.
        Start with a base skeleton and add/remove VMs as needed.

        Args:
            skeleton_name: Base skeleton ("basic-ad", "enterprise-ad", etc.)
            add_vms: List of VM skeleton names to add (e.g., ["sql-server", "exchange"])
            remove_vms: List of VM hostnames to remove
            domain: Custom domain name for AD labs
            siem_type: SIEM type (wazuh, splunk, elastic)
            include_siem: Whether to include SIEM
            include_attacker: Whether to include attacker VM

        Returns:
            Complete customized range configuration

        Example:
            # Start with basic AD and add more servers
            config = await build_range_from_skeleton(
                skeleton_name="basic-ad",
                add_vms=["sql-server", "file-server", "ca"],
                domain="mycorp.local",
                siem_type="splunk"
            )

            # Enterprise AD without Exchange
            config = await build_range_from_skeleton(
                skeleton_name="enterprise-ad",
                remove_vms=["ex01"]
            )
        """
        try:
            # Get base skeleton
            kwargs = {}
            if skeleton_name == "basic-ad":
                if domain:
                    kwargs["domain"] = domain
                kwargs["include_attacker"] = include_attacker
                kwargs["include_siem"] = include_siem
                kwargs["siem_type"] = siem_type
            elif skeleton_name == "enterprise-ad":
                if domain:
                    kwargs["domain"] = domain
            elif skeleton_name == "soc-training":
                kwargs["siem_type"] = siem_type

            config = RangeSkeletons.get_skeleton(skeleton_name, **kwargs)

            # Add VMs from skeletons
            if add_vms:
                next_octet = 50  # Start additional VMs at .50
                for vm_name in add_vms:
                    try:
                        vm_skeleton = VMSkeletons.get_skeleton(vm_name)
                        # Generate unique vm_name
                        vm_skeleton["vm_name"] = f"{{{{ range_id }}}}-{vm_skeleton['hostname']}"
                        vm_skeleton["ip_last_octet"] = next_octet
                        next_octet += 1
                        # Apply domain if specified and VM supports it
                        if domain and "domain" in vm_skeleton:
                            vm_skeleton["domain"]["fqdn"] = domain
                        config["ludus"].append(vm_skeleton)
                    except ValueError:
                        logger.warning(f"Unknown VM skeleton: {vm_name}, skipping")

            # Remove VMs by hostname
            if remove_vms:
                hostnames_to_remove = set(remove_vms)
                config["ludus"] = [
                    vm for vm in config["ludus"]
                    if vm.get("hostname") not in hostnames_to_remove
                ]

            return {
                "status": "success",
                "base_skeleton": skeleton_name,
                "configuration": config,
                "vm_count": len(config.get("ludus", [])),
                "vms_added": len(add_vms) if add_vms else 0,
                "vms_removed": len(remove_vms) if remove_vms else 0,
                "next_steps": [
                    "1. Review the configuration",
                    "2. Export to YAML with export_range_config_to_yaml()",
                    "3. Deploy with ludus range config set -f <file> && ludus range deploy",
                ],
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e),
                "available_range_skeletons": list(RangeSkeletons.list_skeletons().keys()),
                "available_vm_skeletons": list(VMSkeletons.list_skeletons().keys()),
            }

    return mcp


def _apply_customizations(base_config: dict[str, Any], customizations: dict[str, Any]) -> dict[str, Any]:
    """Apply customizations to a base configuration.

    Args:
        base_config: Base range configuration
        customizations: Customizations to apply

    Returns:
        Modified configuration
    """
    import copy

    config = copy.deepcopy(base_config)

    # Add VMs
    if "add_vms" in customizations:
        for vm in customizations["add_vms"]:
            config["ludus"].append(vm)

    # Remove VMs
    if "remove_vms" in customizations:
        vm_names_to_remove = set(customizations["remove_vms"])
        config["ludus"] = [
            vm for vm in config["ludus"]
            if vm.get("vm_name") not in vm_names_to_remove
        ]

    # Modify VMs
    if "modify_vms" in customizations:
        for vm in config["ludus"]:
            vm_name = vm.get("vm_name")
            if vm_name in customizations["modify_vms"]:
                modifications = customizations["modify_vms"][vm_name]
                vm.update(modifications)

    # Add network rules
    if "add_network_rules" in customizations:
        if "network" not in config:
            config["network"] = {"inter_vlan_default": "REJECT", "rules": []}
        for rule in customizations["add_network_rules"]:
            config["network"]["rules"].append(rule)

    # Modify range settings
    if "modify_range_settings" in customizations:
        for key, value in customizations["modify_range_settings"].items():
            config[key] = value

    return config

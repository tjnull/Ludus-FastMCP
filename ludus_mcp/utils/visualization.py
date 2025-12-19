"""ASCII visualization utilities for Ludus ranges."""

from typing import Any


def generate_ascii_topology(config: dict) -> str:
    """
    Generate ASCII art visualization of range topology.

    Args:
        config: Ludus range configuration dictionary

    Returns:
        Formatted ASCII art string showing the range topology
    """
    lines = []

    # Extract range info
    range_name = config.get("name", "Ludus Range")
    range_desc = config.get("description", "")

    # Header
    header = f"  Range: {range_name}  "
    if range_desc:
        header += f"\n  {range_desc}  "

    border_len = max(len(line) for line in header.split('\n')) + 4
    lines.append("╔" + "═" * border_len + "╗")
    for line in header.split('\n'):
        lines.append("║  " + line.ljust(border_len - 2) + "║")
    lines.append("╚" + "═" * border_len + "╝")
    lines.append("")

    # Extract ludus config - can be a list or dict
    ludus_config = config.get("ludus", [])
    
    # Handle both formats: list of VMs or dict with networks/vms
    if isinstance(ludus_config, list):
        # Direct list of VMs
        vms = ludus_config
        networks = []
    elif isinstance(ludus_config, dict):
        # Dict format with networks and vms
        networks = ludus_config.get("networks", [])
        vms = ludus_config.get("vms", [])
    else:
        networks = []
        vms = []

    # Group VMs by network
    vms_by_network = {}
    for vm in vms:
        network = vm.get("network", "unknown")
        if network not in vms_by_network:
            vms_by_network[network] = []
        vms_by_network[network].append(vm)

    # Display networks and VMs
    for network in networks:
        net_name = network.get("name", "unknown")
        net_cidr = network.get("cidr", "")
        net_desc = network.get("description", "")

        lines.append(f"📡 Network: {net_name} ({net_cidr})")
        if net_desc:
            lines.append(f"   {net_desc}")

        # VMs in this network
        network_vms = vms_by_network.get(net_name, [])

        if network_vms:
            for i, vm in enumerate(network_vms):
                is_last = i == len(network_vms) - 1
                prefix = "   └─" if is_last else "   ├─"

                vm_name = vm.get("hostname", vm.get("name", "unknown"))
                vm_template = vm.get("template", "unknown")
                vm_role = vm.get("role", "")

                # Icon based on role or template
                icon = get_vm_icon(vm_template, vm_role)

                lines.append(f"{prefix} {icon} {vm_name} ({vm_template})")

                # Role info
                if vm_role:
                    role_prefix = "       " if is_last else "   │   "
                    lines.append(f"{role_prefix}└─ Role: {vm_role}")

                # Roles (Ansible)
                vm_roles = vm.get("roles", [])
                if vm_roles:
                    role_prefix = "       " if is_last else "   │   "
                    lines.append(f"{role_prefix}└─ Ansible: {', '.join(vm_roles)}")
        else:
            lines.append("   └─ (no VMs)")

        lines.append("")

    # VMs not assigned to networks
    unassigned_vms = [vm for vm in vms if vm.get("network", "unknown") not in [n.get("name") for n in networks]]
    if unassigned_vms:
        lines.append("📡 Network: unassigned")
        for i, vm in enumerate(unassigned_vms):
            is_last = i == len(unassigned_vms) - 1
            prefix = "   └─" if is_last else "   ├─"

            vm_name = vm.get("hostname", vm.get("name", "unknown"))
            vm_template = vm.get("template", "unknown")

            icon = get_vm_icon(vm_template, "")
            lines.append(f"{prefix} {icon} {vm_name} ({vm_template})")
        lines.append("")

    # Summary
    lines.append("═" * 65)
    lines.append(f"Total VMs: {len(vms)}")

    # Estimate deployment time
    estimated_time = estimate_deployment_time(len(vms))
    lines.append(f"Estimated Deploy Time: {estimated_time}")

    # Resource estimates
    total_memory, total_disk = estimate_resources(vms)
    lines.append(f"Estimated Memory: {total_memory}GB")
    lines.append(f"Estimated Disk: {total_disk}GB")
    lines.append("═" * 65)

    return "\n".join(lines)


def get_vm_icon(template: str, role: str) -> str:
    """Get emoji icon for VM based on template and role."""
    template_lower = template.lower()
    role_lower = role.lower()

    # Role-based icons
    if "domain controller" in role_lower or "dc" in role_lower:
        return "🏰"
    if "siem" in role_lower or "wazuh" in role_lower or "splunk" in role_lower:
        return "🛡️"
    if "attacker" in role_lower or "red team" in role_lower:
        return "🐉"
    if "firewall" in role_lower or "router" in role_lower:
        return "🔥"
    if "web" in role_lower or "apache" in role_lower or "nginx" in role_lower:
        return "🌐"
    if "database" in role_lower or "sql" in role_lower or "mysql" in role_lower:
        return "🗄️"

    # Template-based icons
    if "windows-server" in template_lower or "win-server" in template_lower:
        return "🖥️"
    if "windows-11" in template_lower or "win11" in template_lower:
        return "💻"
    if "windows-10" in template_lower or "win10" in template_lower:
        return "💻"
    if "kali" in template_lower:
        return "🐉"
    if "ubuntu" in template_lower or "debian" in template_lower:
        return "🐧"
    if "centos" in template_lower or "rocky" in template_lower or "rhel" in template_lower:
        return "🎩"

    # Default
    return "🖥️"


def estimate_deployment_time(vm_count: int) -> str:
    """Estimate deployment time based on VM count."""
    if vm_count <= 2:
        return "8-12 minutes"
    elif vm_count <= 5:
        return "15-20 minutes"
    elif vm_count <= 10:
        return "25-35 minutes"
    else:
        return f"{vm_count * 3}-{vm_count * 4} minutes"


def estimate_resources(vms: list[dict]) -> tuple[int, int]:
    """
    Estimate total memory and disk requirements.

    Args:
        vms: List of VM configurations

    Returns:
        Tuple of (total_memory_gb, total_disk_gb)
    """
    total_memory = 0
    total_disk = 0

    for vm in vms:
        # Memory (convert MB to GB)
        memory_mb = vm.get("ram_mb", vm.get("memory", 0))
        if memory_mb == 0:
            # Estimate based on template
            template = vm.get("template", "").lower()
            if "server" in template:
                memory_mb = 4096  # 4GB for servers
            elif "windows" in template:
                memory_mb = 4096  # 4GB for Windows desktops
            else:
                memory_mb = 2048  # 2GB for Linux

        total_memory += memory_mb / 1024  # Convert to GB

        # Disk
        disk_gb = vm.get("disk_size_gb", vm.get("disk", 0))
        if disk_gb == 0:
            # Estimate based on template
            template = vm.get("template", "").lower()
            if "windows" in template:
                disk_gb = 60  # 60GB for Windows
            else:
                disk_gb = 30  # 30GB for Linux

        total_disk += disk_gb

    return (int(total_memory), int(total_disk))


def format_scenario_preview(
    scenario_key: str, 
    config: dict, 
    siem_type: str = "wazuh",
    resource_profile: str = "recommended"
) -> str:
    """
    Format a complete scenario preview with detailed information.

    Args:
        scenario_key: Scenario identifier
        config: Ludus range configuration
        siem_type: SIEM type being used
        resource_profile: Resource profile (minimal, recommended, maximum)

    Returns:
        Formatted preview string
    """
    lines = []

    # Title
    lines.append("=" * 80)
    lines.append(f"  SCENARIO PREVIEW: {scenario_key.upper()}")
    lines.append("=" * 80)
    lines.append("")

    # Configuration summary
    lines.append("[CONFIGURATION]")
    lines.append("-" * 80)
    if siem_type and siem_type != "none":
        lines.append(f"  SIEM Platform: {siem_type.title()}")
    else:
        lines.append(f"  SIEM Platform: None")
    lines.append(f"  Resource Profile: {resource_profile.title()}")
    lines.append("")

    # Extract VMs
    vms = config.get("ludus", [])
    if not isinstance(vms, list):
        vms = []

    # Group VMs by VLAN
    vms_by_vlan = {}
    for vm in vms:
        vlan = vm.get("vlan", "unknown")
        if vlan not in vms_by_vlan:
            vms_by_vlan[vlan] = []
        vms_by_vlan[vlan].append(vm)

    # VM Details
    lines.append("[VIRTUAL MACHINES]")
    lines.append("-" * 80)
    lines.append(f"  Total VMs: {len(vms)}")
    lines.append("")

    # Show VMs grouped by VLAN
    for vlan in sorted(vms_by_vlan.keys(), key=lambda x: x if isinstance(x, int) else 0):
        vlan_vms = vms_by_vlan[vlan]
        lines.append(f"  VLAN {vlan} ({len(vlan_vms)} VM{'s' if len(vlan_vms) != 1 else ''}):")
        
        for vm in vlan_vms:
            vm_name = vm.get("hostname", vm.get("vm_name", "unknown"))
            template = vm.get("template", "unknown")
            ram_gb = vm.get("ram_gb", 0)
            cpus = vm.get("cpus", 0)
            ip_octet = vm.get("ip_last_octet", "?")
            ip_base = f"192.168.{vlan}.{ip_octet}" if isinstance(vlan, int) else "N/A"
            
            # Get roles
            roles = vm.get("roles", [])
            if not roles and "ansible_roles" in vm:
                ansible_roles = vm.get("ansible_roles", [])
                if isinstance(ansible_roles, list):
                    roles = [r.get("name") if isinstance(r, dict) else r for r in ansible_roles]
            
            lines.append(f"    • {vm_name}")
            lines.append(f"      Template: {template}")
            lines.append(f"      Resources: {ram_gb}GB RAM, {cpus} CPUs")
            lines.append(f"      IP: {ip_base}")
            if roles:
                lines.append(f"      Roles: {', '.join(roles[:3])}")
                if len(roles) > 3:
                    lines.append(f"             + {len(roles) - 3} more")
            lines.append("")
    
    # Network Rules
    network_rules = config.get("network", {}).get("rules", [])
    if network_rules:
        lines.append("[NETWORK RULES]")
        lines.append("-" * 80)
        lines.append(f"  Total Rules: {len(network_rules)}")
        for rule in network_rules[:5]:  # Show first 5
            name = rule.get("name", "unnamed")
            src = rule.get("vlan_src", "?")
            dst = rule.get("vlan_dst", "?")
            action = rule.get("action", "ACCEPT")
            lines.append(f"    • {name}: VLAN {src} -> VLAN {dst} ({action})")
        if len(network_rules) > 5:
            lines.append(f"    ... and {len(network_rules) - 5} more rules")
        lines.append("")

    # Resource Summary
    total_ram = sum(vm.get("ram_gb", 0) for vm in vms)
    total_cpus = sum(vm.get("cpus", 0) for vm in vms)
    estimated_time = estimate_deployment_time(len(vms))
    estimated_memory_gb, estimated_disk_gb = estimate_resources(vms)
    
    lines.append("[RESOURCE SUMMARY]")
    lines.append("-" * 80)
    lines.append(f"  Total RAM: {total_ram}GB")
    lines.append(f"  Total CPUs: {total_cpus}")
    lines.append(f"  Estimated Disk: {estimated_disk_gb}GB")
    lines.append(f"  Estimated Deployment Time: {estimated_time}")
    lines.append("")

    # Deployment Commands
    lines.append("[DEPLOYMENT]")
    lines.append("-" * 80)
    lines.append("  To deploy this scenario:")
    lines.append(f"    ludus.deploy_scenario(scenario_key='{scenario_key}', siem_type='{siem_type}')")
    lines.append("")
    lines.append("  Or use smart deploy for auto-monitoring:")
    lines.append(f"    ludus.smart_deploy(scenario_key='{scenario_key}', siem_type='{siem_type}')")
    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_deployment_status(status_data: dict) -> str:
    """
    Format deployment status with visual indicators.

    Args:
        status_data: Deployment status dictionary

    Returns:
        Formatted status string
    """
    state = status_data.get("rangeState", "UNKNOWN")
    vm_count = status_data.get("numberOfVMs", 0)

    # Status indicator
    status_indicator = {
        "SUCCESS": "[OK]",
        "DEPLOYING": "[...]",
        "FAILED": "[ERROR]",
        "DELETED": "[DELETED]",
        "UNKNOWN": "[?]"
    }

    indicator = status_indicator.get(state, "[?]")

    # Build status line
    status_line = f"{indicator} Range Status: {state}"

    if vm_count > 0:
        status_line += f" | VMs: {vm_count}"

    # Add timing info if available
    if "lastDeployment" in status_data:
        last_deploy = status_data["lastDeployment"]
        status_line += f" | Deployed: {last_deploy}"

    return status_line


def format_progress_bar(percentage: float, width: int = 40) -> str:
    """
    Generate ASCII progress bar.

    Args:
        percentage: Progress percentage (0-100)
        width: Width of progress bar in characters

    Returns:
        Formatted progress bar string
    """
    filled = int(width * percentage / 100)
    empty = width - filled

    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percentage:.0f}%"


def format_vm_list(vms: list[dict]) -> str:
    """
    Format VM list with status indicators.

    Args:
        vms: List of VM dictionaries

    Returns:
        Formatted VM list string
    """
    if not vms:
        return "No VMs found"

    lines = []
    lines.append("Virtual Machines:")
    lines.append("-" * 60)

    for vm in vms:
        name = vm.get("hostname", vm.get("name", "unknown"))
        template = vm.get("template", "unknown")
        network = vm.get("network", "unknown")
        status = vm.get("status", "unknown")

        # Status icon
        status_icon = "[OK]" if status == "running" else "[STOPPED]" if status == "stopped" else "[?]"

        lines.append(f"{status_icon} {name}")
        lines.append(f"   Template: {template}")
        lines.append(f"   Network: {network}")
        if status:
            lines.append(f"   Status: {status}")
        lines.append("")

    return "\n".join(lines)


def format_network_list(networks: list[dict]) -> str:
    """
    Format network list.

    Args:
        networks: List of network dictionaries

    Returns:
        Formatted network list string
    """
    if not networks:
        return "No networks found"

    lines = []
    lines.append("Networks:")
    lines.append("-" * 60)

    for net in networks:
        name = net.get("name", "unknown")
        cidr = net.get("cidr", "unknown")
        vlan = net.get("vlan", "")

        lines.append(f"📡 {name} ({cidr})")
        if vlan:
            lines.append(f"   VLAN: {vlan}")
        lines.append("")

    return "\n".join(lines)


def generate_deployment_summary(range_data: dict, logs_preview: str = "") -> str:
    """
    Generate comprehensive deployment summary.

    Args:
        range_data: Range information dictionary
        logs_preview: Optional logs preview

    Returns:
        Formatted summary string
    """
    lines = []

    # Header
    lines.append("╔" + "═" * 63 + "╗")
    lines.append("║" + "  Deployment Summary".ljust(63) + "║")
    lines.append("╚" + "═" * 63 + "╝")
    lines.append("")

    # Status
    state = range_data.get("rangeState", "UNKNOWN")
    status_indicator = {
        "SUCCESS": "[OK]",
        "DEPLOYING": "[...]",
        "FAILED": "[ERROR]",
        "DELETED": "[DELETED]",
        "UNKNOWN": "[?]"
    }
    indicator = status_indicator.get(state, "[?]")

    lines.append(f"Status: {indicator} {state}")
    lines.append(f"VMs: {range_data.get('numberOfVMs', 0)}")
    lines.append("")

    # Logs preview
    if logs_preview:
        lines.append("Recent Logs:")
        lines.append("-" * 60)
        lines.append(logs_preview)
        lines.append("")

    # Next steps based on state
    lines.append("Next Steps:")
    if state == "DEPLOYING":
        lines.append("  • Wait for deployment to complete (check status periodically)")
        lines.append("  • Use: ludus.get_deployment_status")
        lines.append("  • Check health: ludus.check_deployment_health")
    elif state == "SUCCESS":
        lines.append("  • Get access info: ludus.get_range_sshconfig")
        lines.append("  • Get RDP configs: ludus.get_range_rdpconfigs")
        lines.append("  • Start testing: ludus.start_testing")
    elif state == "FAILED":
        lines.append("  • Check logs: ludus.get_full_logs")
        lines.append("  • Check health: ludus.check_deployment_health")
        lines.append("  • Get recovery help: ludus.recover_deployment")

    return "\n".join(lines)

"""Error formatting utilities for better user feedback."""

from typing import Any


class ErrorFormatter:
    """Format errors with actionable guidance for users."""

    # Common error patterns and their explanations
    ERROR_PATTERNS = {
        "active directory web services": {
            "title": "Active Directory Web Services Not Running",
            "meaning": (
                "The Domain Controller VM is running, but AD Web Services hasn't "
                "started yet. This is normal during initial DC setup."
            ),
            "severity": "transient",
            "actions": [
                "- Wait 5-10 minutes for AD services to fully initialize",
                "- Ludus will automatically retry the failed tasks",
                "- Check status: ludus.quick_status",
                "- View logs: ludus.get_full_logs"
            ],
            "note": "This is a TRANSIENT error - it typically resolves automatically.",
            "next_steps": [
                "1. Check status in 5 minutes: ludus.quick_status",
                "2. If still failing after 15 min: ludus.check_deployment_health",
                "3. View full diagnostics: ludus.get_full_logs"
            ]
        },
        "template not found": {
            "title": "VM Template Not Found",
            "meaning": (
                "The specified VM template doesn't exist in your Ludus environment."
            ),
            "severity": "error",
            "actions": [
                "- List available templates: ludus.list_templates",
                "- Check template name spelling",
                "- Verify template is installed in Ludus",
                "- Update configuration with correct template name"
            ],
            "note": "This requires configuration changes before redeploying.",
            "next_steps": [
                "1. List templates: ludus.list_templates",
                "2. Fix config with correct template",
                "3. Validate config: ludus.validate_config(config)",
                "4. Redeploy: ludus.deploy_range"
            ]
        },
        "role not found": {
            "title": "Ansible Role Not Installed",
            "meaning": (
                "An Ansible role required by your configuration is not installed."
            ),
            "severity": "warning",
            "actions": [
                "- Ludus may auto-install the role if available",
                "- List installed roles: ludus.list_roles",
                "- Install manually if needed",
                "- Or remove role from configuration"
            ],
            "note": "Ludus often auto-installs missing roles during deployment.",
            "next_steps": [
                "1. Check if deployment continues (auto-install)",
                "2. List roles: ludus.list_roles",
                "3. If deployment fails, remove role or install manually"
            ]
        },
        "connection refused": {
            "title": "Network Connection Refused",
            "meaning": (
                "Ludus cannot connect to a VM. The VM may not be fully booted or "
                "network services may not be ready."
            ),
            "severity": "warning",
            "actions": [
                "- Wait for VMs to fully boot",
                "- Check VM power state: ludus.get_range",
                "- Verify network configuration",
                "- Check firewall rules"
            ],
            "note": "VMs may need a few minutes to boot and start network services.",
            "next_steps": [
                "1. Wait 2-3 minutes for VMs to boot",
                "2. Check VM status: ludus.get_range",
                "3. Review network config if persists"
            ]
        },
        "timeout": {
            "title": "Operation Timeout",
            "meaning": (
                "An operation took longer than expected. This could be due to slow "
                "VM boot, network latency, or resource constraints."
            ),
            "severity": "warning",
            "actions": [
                "- Wait - operation may still complete",
                "- Check host resources (CPU, RAM, disk)",
                "- Monitor deployment: ludus.get_deployment_status",
                "- Ludus will retry automatically"
            ],
            "note": "Timeouts often resolve themselves. Ludus will retry.",
            "next_steps": [
                "1. Monitor status: ludus.quick_status",
                "2. Check health: ludus.check_deployment_health",
                "3. If persistent, check host resources"
            ]
        },
        "unreachable": {
            "title": "Host Unreachable",
            "meaning": (
                "A VM is unreachable by Ansible. The VM may be powered off, "
                "not fully booted, or having network issues."
            ),
            "severity": "warning",
            "actions": [
                "- Check VM power state: ludus.get_range",
                "- Verify VM is fully booted (check console)",
                "- Check network connectivity",
                "- Review firewall rules"
            ],
            "note": "VMs need time to boot before Ansible can connect.",
            "next_steps": [
                "1. Check VMs are running: ludus.get_range",
                "2. Wait 3-5 minutes for boot",
                "3. Check logs: ludus.get_full_logs"
            ]
        },
        "fatal": {
            "title": "Fatal Error",
            "meaning": (
                "A critical error occurred that cannot be automatically recovered."
            ),
            "severity": "error",
            "actions": [
                "- Review full logs: ludus.get_full_logs",
                "- Identify root cause",
                "- Fix configuration",
                "- Consider destroying and redeploying"
            ],
            "note": "This may require manual intervention.",
            "next_steps": [
                "1. Get full logs: ludus.get_full_logs",
                "2. Fix identified issues",
                "3. Consider: ludus.should_destroy_range",
                "4. Redeploy with fixes"
            ]
        },
        "authentication failed": {
            "title": "API Authentication Failed",
            "meaning": (
                "The provided API key is invalid, expired, or not set correctly."
            ),
            "severity": "error",
            "actions": [
                "- Verify LUDUS_API_KEY is set correctly",
                "- Generate new API key: ludus user apikey",
                "- Check API key has not expired",
                "- Ensure no extra whitespace in key"
            ],
            "note": "API keys can be regenerated from the Ludus CLI.",
            "next_steps": [
                "1. Run: ludus user apikey (to get/regenerate key)",
                "2. Update LUDUS_API_KEY environment variable",
                "3. Restart MCP server",
                "4. Test connection: health_check"
            ]
        },
        "permission denied": {
            "title": "Permission Denied",
            "meaning": (
                "Your user account does not have permission for this operation. "
                "Admin privileges may be required."
            ),
            "severity": "error",
            "actions": [
                "- Check if operation requires admin privileges",
                "- Verify you're using the correct user",
                "- Contact Ludus administrator",
                "- Review Ludus role permissions"
            ],
            "note": "Some operations (user management, admin templates) require admin role.",
            "next_steps": [
                "1. Check your user role: ludus.get_user",
                "2. Contact admin if elevated access needed",
                "3. Use non-admin alternatives if available"
            ]
        },
        "cannot connect": {
            "title": "Cannot Connect to Ludus Server",
            "meaning": (
                "The MCP server cannot reach the Ludus API. The server may be down, "
                "the URL may be incorrect, or there may be network issues."
            ),
            "severity": "error",
            "actions": [
                "- Verify LUDUS_API_URL is correct",
                "- Check Ludus server is running",
                "- Verify network connectivity/VPN",
                "- Check firewall rules allow connection"
            ],
            "note": "Ensure you can reach the Ludus URL from your machine.",
            "next_steps": [
                "1. Ping/curl the Ludus server URL",
                "2. Verify LUDUS_API_URL setting",
                "3. Check VPN connection if required",
                "4. Test: health_check"
            ]
        },
        "rate limit": {
            "title": "Rate Limit Exceeded",
            "meaning": (
                "Too many API requests have been made in a short time. "
                "The rate limiter is protecting the Ludus server."
            ),
            "severity": "warning",
            "actions": [
                "- Wait a few seconds before retrying",
                "- Reduce request frequency",
                "- Check if requests are being duplicated",
                "- Consider batching operations"
            ],
            "note": "The rate limiter resets automatically. Wait and retry.",
            "next_steps": [
                "1. Wait 30-60 seconds",
                "2. Retry the operation",
                "3. If persistent, reduce operation frequency"
            ]
        },
        "ssl": {
            "title": "SSL/TLS Certificate Error",
            "meaning": (
                "There's an issue with the SSL certificate. This is common in lab "
                "environments using self-signed certificates."
            ),
            "severity": "warning",
            "actions": [
                "- For self-signed certs: Set LUDUS_SSL_VERIFY=false",
                "- For valid certs: Verify certificate chain",
                "- Check certificate hasn't expired",
                "- Verify URL uses correct protocol (https vs http)"
            ],
            "note": "Self-signed certs are common in lab environments. SSL verify is disabled by default.",
            "next_steps": [
                "1. Check LUDUS_SSL_VERIFY setting",
                "2. Verify LUDUS_API_URL protocol",
                "3. If using valid cert, check certificate validity"
            ]
        },
        "disk space": {
            "title": "Insufficient Disk Space",
            "meaning": (
                "The Ludus host or VM storage is running low on disk space. "
                "This can prevent VM creation and deployment."
            ),
            "severity": "error",
            "actions": [
                "- Check Proxmox storage usage",
                "- Delete unused VMs and templates",
                "- Remove old snapshots",
                "- Expand storage if possible"
            ],
            "note": "VMs and templates require significant disk space.",
            "next_steps": [
                "1. Delete unused ranges: ludus.delete_range",
                "2. Remove old snapshots: ludus.remove_snapshot",
                "3. Check Proxmox storage dashboard",
                "4. Contact admin if storage expansion needed"
            ]
        },
        "memory": {
            "title": "Insufficient Memory",
            "meaning": (
                "Not enough RAM available on the Ludus host to deploy VMs. "
                "Reduce VM count or RAM allocation per VM."
            ),
            "severity": "error",
            "actions": [
                "- Reduce number of VMs in range",
                "- Lower RAM allocation per VM",
                "- Power off unused ranges",
                "- Check host memory usage in Proxmox"
            ],
            "note": "Each VM requires dedicated RAM. Plan capacity accordingly.",
            "next_steps": [
                "1. Power off unused ranges: ludus.power_off_range",
                "2. Use minimal resource profile",
                "3. Reduce VM count in configuration",
                "4. Check Proxmox memory dashboard"
            ]
        },
        "winrm": {
            "title": "WinRM Connection Failed",
            "meaning": (
                "Cannot connect to Windows VM via WinRM. The WinRM service "
                "may not be running or properly configured."
            ),
            "severity": "warning",
            "actions": [
                "- Wait for Windows VM to fully boot",
                "- WinRM starts after initial setup",
                "- Check firewall allows WinRM (5985/5986)",
                "- Verify Windows credentials"
            ],
            "note": "Windows VMs need time to boot and start WinRM service.",
            "next_steps": [
                "1. Wait 5-10 minutes for Windows to boot fully",
                "2. Check VM power state: ludus.get_range",
                "3. Verify WinRM ports are open",
                "4. Review deployment logs: ludus.get_full_logs"
            ]
        },
        "ssh": {
            "title": "SSH Connection Failed",
            "meaning": (
                "Cannot connect to Linux VM via SSH. The VM may not be booted, "
                "SSH service not running, or firewall blocking connection."
            ),
            "severity": "warning",
            "actions": [
                "- Wait for Linux VM to fully boot",
                "- Verify SSH service is enabled",
                "- Check firewall allows SSH (port 22)",
                "- Verify SSH key/credentials"
            ],
            "note": "Linux VMs typically boot faster but still need initialization time.",
            "next_steps": [
                "1. Wait 2-3 minutes for boot",
                "2. Check VM status: ludus.get_range",
                "3. Get SSH config: ludus.get_range_sshconfig",
                "4. Verify network connectivity"
            ]
        },
        "already exists": {
            "title": "Resource Already Exists",
            "meaning": (
                "The resource you're trying to create already exists. "
                "This could be a range, snapshot, template, or user."
            ),
            "severity": "warning",
            "actions": [
                "- Use a different name",
                "- Delete existing resource first",
                "- Update existing instead of create",
                "- Check if existing resource meets your needs"
            ],
            "note": "Resource names must be unique within their scope.",
            "next_steps": [
                "1. List existing resources",
                "2. Choose a unique name",
                "3. Or delete existing: ludus.delete_range/remove_snapshot"
            ]
        },
        "not found": {
            "title": "Resource Not Found",
            "meaning": (
                "The requested resource doesn't exist. It may have been deleted, "
                "never created, or the name is incorrect."
            ),
            "severity": "error",
            "actions": [
                "- Verify resource name spelling",
                "- Check if resource was deleted",
                "- List available resources",
                "- Create the resource if needed"
            ],
            "note": "Double-check resource names - they are case-sensitive.",
            "next_steps": [
                "1. List resources: ludus.get_range, ludus.list_templates",
                "2. Verify exact name/ID",
                "3. Create resource if needed"
            ]
        },
        "proxmox": {
            "title": "Proxmox Error",
            "meaning": (
                "An error occurred in the Proxmox virtualization layer. "
                "This could be a storage, network, or VM operation issue."
            ),
            "severity": "error",
            "actions": [
                "- Check Proxmox web interface for details",
                "- Review Proxmox logs",
                "- Verify Proxmox cluster health",
                "- Check storage and network status"
            ],
            "note": "Proxmox errors often require admin-level troubleshooting.",
            "next_steps": [
                "1. Access Proxmox web UI",
                "2. Check cluster status",
                "3. Review task history for errors",
                "4. Contact Ludus/Proxmox admin"
            ]
        }
    }

    @classmethod
    def format_error(cls, error_text: str, context: dict[str, Any] | None = None) -> str:
        """
        Format an error with helpful guidance.

        Args:
            error_text: Error message or log text
            context: Additional context (range state, etc.)

        Returns:
            Formatted error message with guidance
        """
        error_lower = error_text.lower()

        # Find matching error pattern
        pattern_info = None
        for pattern, info in cls.ERROR_PATTERNS.items():
            if pattern in error_lower:
                pattern_info = info
                break

        if not pattern_info:
            # Generic error formatting
            return cls._format_generic_error(error_text, context)

        # Format known error
        lines = []
        lines.append("")
        lines.append("[ERROR] " + pattern_info["title"])
        lines.append("")
        lines.append("What this means:")
        lines.append("  " + pattern_info["meaning"])
        lines.append("")
        lines.append("What to do:")
        for action in pattern_info["actions"]:
            lines.append("  " + action)
        lines.append("")
        lines.append(pattern_info["note"])
        lines.append("")
        lines.append("Next steps:")
        for step in pattern_info["next_steps"]:
            lines.append("  " + step)
        lines.append("")

        # Add context if available
        if context:
            range_state = context.get("range_state")
            if range_state:
                lines.append(f"Current Range State: {range_state}")
                lines.append("")

        return "\n".join(lines)

    @classmethod
    def _format_generic_error(cls, error_text: str, context: dict[str, Any] | None = None) -> str:
        """Format a generic error without specific guidance."""
        lines = []
        lines.append("")
        lines.append("[ERROR] Deployment Error")
        lines.append("")
        lines.append("Error details:")
        lines.append("  " + error_text[:500])  # Limit error text length
        lines.append("")
        lines.append("Suggested actions:")
        lines.append("  - Check full logs: ludus.get_full_logs")
        lines.append("  - Check health: ludus.check_deployment_health")
        lines.append("  - Review configuration")
        lines.append("  - Check Ludus documentation")
        lines.append("")

        if context:
            range_state = context.get("range_state")
            if range_state:
                lines.append(f"Current Range State: {range_state}")
                lines.append("")

        return "\n".join(lines)

    @classmethod
    def format_validation_errors(cls, errors: list[Any], warnings: list[Any] | None = None) -> str:
        """
        Format validation errors and warnings.

        Args:
            errors: List of validation errors
            warnings: Optional list of warnings

        Returns:
            Formatted validation report
        """
        lines = []
        lines.append("")
        lines.append("╔" + "═" * 63 + "╗")
        lines.append("║" + "  Configuration Validation Report".ljust(63) + "║")
        lines.append("╚" + "═" * 63 + "╝")
        lines.append("")

        if errors:
            lines.append("[ERROR] ERRORS (must fix before deployment):")
            lines.append("")
            for error in errors:
                field = error.get("field", "unknown")
                message = error.get("message", "")
                lines.append(f"  • Field: {field}")
                lines.append(f"    {message}")
                lines.append("")

        if warnings:
            lines.append("[WARNING] WARNINGS (recommended to review):")
            lines.append("")
            for warning in warnings:
                field = warning.get("field", "unknown")
                message = warning.get("message", "")
                lines.append(f"  • Field: {field}")
                lines.append(f"    {message}")
                lines.append("")

        if not errors:
            lines.append("[OK] No errors found!")
            lines.append("")
            lines.append("Configuration is valid and ready to deploy.")
            lines.append("")

        lines.append("Next steps:")
        if errors:
            lines.append("  1. Fix the errors listed above")
            lines.append("  2. Validate again: ludus.validate_config(config)")
            lines.append("  3. Deploy: ludus.deploy_range or ludus.smart_deploy")
        else:
            lines.append("  1. Preview scenario: ludus.preview_scenario")
            lines.append("  2. Deploy: ludus.smart_deploy (recommended)")
            lines.append("     Or: ludus.deploy_range")

        lines.append("")
        return "\n".join(lines)

    @classmethod
    def format_deployment_failure(cls, logs: str, range_state: str) -> str:
        """
        Format a deployment failure message with guidance.

        Args:
            logs: Deployment logs
            range_state: Current range state

        Returns:
            Formatted failure message
        """
        lines = []
        lines.append("")
        lines.append("╔" + "═" * 63 + "╗")
        lines.append("║" + "  Deployment Failed".ljust(63) + "║")
        lines.append("╚" + "═" * 63 + "╝")
        lines.append("")
        lines.append(f"Current State: {range_state}")
        lines.append("")

        # Analyze logs for known patterns
        found_patterns = []
        for pattern, info in cls.ERROR_PATTERNS.items():
            if pattern in logs.lower():
                found_patterns.append((pattern, info))

        if found_patterns:
            lines.append("Identified Issues:")
            lines.append("")
            for pattern, info in found_patterns:
                lines.append(f"  • {info['title']}")
                severity_icon = "[WARNING]" if info["severity"] in ["warning", "transient"] else "[ERROR]"
                lines.append(f"    {severity_icon} Severity: {info['severity']}")
                lines.append(f"    {info['meaning']}")
                lines.append("")

            # Provide guidance for the most severe issue
            primary_issue = found_patterns[0][1]
            lines.append("Recommended Actions:")
            for action in primary_issue["actions"]:
                lines.append("  " + action)
            lines.append("")

            lines.append("Next Steps:")
            for step in primary_issue["next_steps"]:
                lines.append("  " + step)
        else:
            # Generic failure guidance
            lines.append("No specific error pattern identified.")
            lines.append("")
            lines.append("Recommended Actions:")
            lines.append("  - Review full logs: ludus.get_full_logs")
            lines.append("  - Check deployment health: ludus.check_deployment_health")
            lines.append("  - Get recovery guidance: ludus.recover_deployment")

        lines.append("")
        return "\n".join(lines)


def format_success_message(scenario_key: str, range_info: dict) -> str:
    """
    Format a deployment success message.

    Args:
        scenario_key: Scenario that was deployed
        range_info: Range information

    Returns:
        Formatted success message
    """
    lines = []
    lines.append("")
    lines.append("╔" + "═" * 63 + "╗")
    lines.append("║" + "  Deployment Complete!".ljust(63) + "║")
    lines.append("╚" + "═" * 63 + "╝")
    lines.append("")
    lines.append(f"Scenario: {scenario_key}")
    lines.append(f"VMs: {range_info.get('numberOfVMs', 0)}")
    lines.append("")

    # List VMs
    vms = range_info.get("VMs", [])
    if vms:
        lines.append("Your lab is ready:")
        for vm in vms:
            hostname = vm.get("hostname", "unknown")
            ip = vm.get("ip", "unknown")
            role = vm.get("role", "")
            lines.append(f"  [OK] {hostname} ({ip}){' - ' + role if role else ''}")
        lines.append("")

    lines.append("Access Info:")
    lines.append("  • RDP configs: ludus.get_range_rdpconfigs")
    lines.append("  • SSH config: ludus.get_range_sshconfig")
    lines.append("  • Range details: ludus.get_range")
    lines.append("")

    lines.append("Next Steps:")
    lines.append("  1. Start testing: ludus.start_testing")
    lines.append("  2. Create snapshot: ludus.snapshot_host")
    lines.append("  3. Check SIEM: ludus.get_siem_info (if SIEM deployed)")
    lines.append("")

    lines.append("Ready to start testing!")
    lines.append("")

    return "\n".join(lines)

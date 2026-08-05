"""Handler for documentation and knowledge base operations."""

from datetime import datetime
from typing import Any
import json

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class DocumentationHandler:
    """Handler for documentation and knowledge base."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the documentation handler."""
        self.client = client

    async def _optional_ssh_config(self, user_id: str | None) -> str:
        """Fetch the SSH config, tolerating servers that do not provide one.

        /range/sshconfig returns HTTP 501 on some Ludus builds. It is a
        convenience section of the document, so letting it fail would throw away
        an otherwise complete set of range documentation.
        """
        try:
            return await self.client.get_range_sshconfig(user_id)
        except Exception as e:
            logger.warning(f"SSH config unavailable, omitting from documentation: {e}")
            return "SSH config is not available from this Ludus server."

    async def generate_range_documentation(
        self,
        format: str = "markdown",
        include_credentials: bool = False,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Auto-generate range documentation."""
        try:
            range_info = await self.client.get_range(user_id)
            range_config = await self.client.get_range_config(user_id)
            ssh_config = await self._optional_ssh_config(user_id)

            vms = range_info.get("VMs", [])

            if format == "markdown":
                doc = self._generate_markdown_doc(range_info, range_config, vms, ssh_config, include_credentials)
            elif format == "html":
                doc = self._generate_html_doc(range_info, range_config, vms, include_credentials)
            elif format == "pdf":
                doc = "PDF generation requires wkhtmltopdf or similar. Generate HTML first then convert."
            else:
                return {"status": "error", "error": f"Unsupported format: {format}"}

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "format": format,
                "documentation": doc,
                "vm_count": len(vms),
                "includes_credentials": include_credentials
            }
        except Exception as e:
            logger.error(f"Error generating documentation: {e}")
            return {"status": "error", "error": str(e)}

    def _generate_markdown_doc(self, range_info, range_config, vms, ssh_config, include_creds):
        """Generate Markdown documentation."""
        lines = [
            f"# Range Documentation",
            f"",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## Overview",
            f"",
            f"- **Range State:** {range_info.get('rangeState')}",
            f"- **Total VMs:** {len(vms)}",
            f"- **Testing Enabled:** {range_info.get('testingEnabled')}",
            f"",
            f"## Virtual Machines",
            f""
        ]

        for vm in vms:
            lines.append(f"### {vm.get('name', 'Unknown')}")
            lines.append(f"")
            lines.append(f"- **Status:** {vm.get('status', 'unknown')}")
            lines.append(f"- **Template:** {vm.get('template', 'unknown')}")
            lines.append(f"- **IP Address:** {vm.get('ip', 'unknown')}")
            lines.append(f"- **Memory:** {vm.get('memory', 'unknown')} MB")
            lines.append(f"- **CPUs:** {vm.get('cpus', 'unknown')}")
            lines.append(f"")

        lines.append(f"## SSH Configuration")
        lines.append(f"")
        lines.append(f"```")
        lines.append(ssh_config[:500] if ssh_config else "No SSH config available")
        lines.append(f"```")
        lines.append(f"")

        return "\n".join(lines)

    def _generate_html_doc(self, range_info, range_config, vms, include_creds):
        """Generate HTML documentation."""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Range Documentation</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Range Documentation</h1>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <h2>Virtual Machines</h2>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>IP</th>
                    <th>Template</th>
                </tr>
        """

        for vm in vms:
            html += f"""
                <tr>
                    <td>{vm.get('name', 'Unknown')}</td>
                    <td>{vm.get('status', 'unknown')}</td>
                    <td>{vm.get('ip', 'unknown')}</td>
                    <td>{vm.get('template', 'unknown')}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """
        return html

    async def get_attack_path_documentation(
        self,
        scenario_name: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Detailed attack paths for deployed scenarios."""
        try:
            # Attack path templates for common scenarios
            attack_paths = {
                "kerberoasting": {
                    "objective": "Compromise domain through Kerberoasting attack",
                    "steps": [
                        {"step": 1, "action": "Initial access on workstation", "tools": ["evil-winrm", "RDP"]},
                        {"step": 2, "action": "Domain enumeration", "tools": ["BloodHound", "PowerView"]},
                        {"step": 3, "action": "Request service tickets", "tools": ["Rubeus", "Invoke-Kerberoast"]},
                        {"step": 4, "action": "Crack service account passwords", "tools": ["Hashcat", "John"]},
                        {"step": 5, "action": "Authenticate as service account", "tools": ["evil-winrm"]},
                        {"step": 6, "action": "Escalate to domain admin", "tools": ["mimikatz", "DCSync"]}
                    ]
                },
                "golden-ticket": {
                    "objective": "Create golden ticket for persistent domain access",
                    "steps": [
                        {"step": 1, "action": "Compromise domain controller", "tools": ["exploit", "Pass-the-Hash"]},
                        {"step": 2, "action": "Extract KRBTGT hash", "tools": ["mimikatz", "DCSync"]},
                        {"step": 3, "action": "Create golden ticket", "tools": ["mimikatz"]},
                        {"step": 4, "action": "Use ticket for access", "tools": ["mimikatz", "Rubeus"]},
                        {"step": 5, "action": "Establish persistence", "tools": ["scheduled tasks", "WMI"]}
                    ]
                }
            }

            if scenario_name not in attack_paths:
                return {
                    "status": "error",
                    "error": f"No attack path documentation for scenario: {scenario_name}",
                    "available_scenarios": list(attack_paths.keys())
                }

            path = attack_paths[scenario_name]

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "scenario": scenario_name,
                "attack_path": path,
                "total_steps": len(path["steps"]),
                "difficulty": "intermediate"
            }
        except Exception as e:
            logger.error(f"Error getting attack path documentation: {e}")
            return {"status": "error", "error": str(e)}

    async def export_lab_guide(
        self,
        title: str,
        difficulty: str = "intermediate",
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Generate student/participant lab guides."""
        try:
            range_info = await self.client.get_range(user_id)
            ssh_config = await self._optional_ssh_config(user_id)

            vms = range_info.get("VMs", [])

            lab_guide = f"""
# {title}

**Difficulty:** {difficulty.upper()}
**Duration:** 2-4 hours
**Generated:** {datetime.now().strftime('%Y-%m-%d')}

## Objectives

1. Enumerate the network and identify targets
2. Gain initial access to systems
3. Escalate privileges
4. Achieve objectives and document findings

## Lab Environment

### Available Systems

"""
            for vm in vms:
                lab_guide += f"- **{vm.get('name')}**: {vm.get('template', 'Unknown')} ({vm.get('ip', 'N/A')})\n"

            lab_guide += f"""

### Access Information

Use the provided SSH configuration to access systems.

## Tasks

### Task 1: Reconnaissance
- Perform network scanning
- Identify running services
- Map the network topology

### Task 2: Initial Access
- Identify vulnerabilities
- Exploit discovered weaknesses
- Gain initial foothold

### Task 3: Privilege Escalation
- Enumerate user privileges
- Find escalation paths
- Gain administrative access

### Task 4: Post-Exploitation
- Document findings
- Collect evidence
- Demonstrate impact

## Submission

Document your methodology, tools used, and findings in a professional report.

---
*This lab environment is for authorized testing only.*
"""

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "title": title,
                "difficulty": difficulty,
                "lab_guide": lab_guide,
                "vm_count": len(vms)
            }
        except Exception as e:
            logger.error(f"Error exporting lab guide: {e}")
            return {"status": "error", "error": str(e)}

    async def create_scenario_playbook(
        self,
        scenario_name: str,
        team: str = "red",
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Generate red/blue team playbooks."""
        try:
            if team not in ["red", "blue", "purple"]:
                return {"status": "error", "error": "Team must be 'red', 'blue', or 'purple'"}

            playbook = {
                "scenario": scenario_name,
                "team": team,
                "created_at": datetime.now().isoformat(),
                "phases": []
            }

            if team == "red":
                playbook["phases"] = [
                    {
                        "phase": "Reconnaissance",
                        "objectives": ["Map network", "Identify targets", "Enumerate services"],
                        "tools": ["nmap", "masscan", "enum4linux"],
                        "duration_hours": 0.5
                    },
                    {
                        "phase": "Initial Access",
                        "objectives": ["Exploit vulnerabilities", "Gain foothold", "Establish C2"],
                        "tools": ["Metasploit", "Cobalt Strike", "Empire"],
                        "duration_hours": 1
                    },
                    {
                        "phase": "Privilege Escalation",
                        "objectives": ["Escalate privileges", "Gain admin access"],
                        "tools": ["mimikatz", "PowerUp", "LinPEAS"],
                        "duration_hours": 1
                    },
                    {
                        "phase": "Lateral Movement",
                        "objectives": ["Move across network", "Compromise additional systems"],
                        "tools": ["PsExec", "WMI", "SSH"],
                        "duration_hours": 1.5
                    }
                ]
            elif team == "blue":
                playbook["phases"] = [
                    {
                        "phase": "Monitoring",
                        "objectives": ["Monitor SIEM alerts", "Analyze logs", "Detect anomalies"],
                        "tools": ["Splunk", "ELK", "Wazuh"],
                        "duration_hours": "continuous"
                    },
                    {
                        "phase": "Investigation",
                        "objectives": ["Investigate alerts", "Identify IOCs", "Determine scope"],
                        "tools": ["Wireshark", "Sysmon", "OSQuery"],
                        "duration_hours": "as_needed"
                    },
                    {
                        "phase": "Response",
                        "objectives": ["Contain threat", "Eradicate malware", "Recover systems"],
                        "tools": ["EDR", "Firewall", "IPS"],
                        "duration_hours": "as_needed"
                    }
                ]

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "playbook": playbook,
                "total_phases": len(playbook["phases"])
            }
        except Exception as e:
            logger.error(f"Error creating playbook: {e}")
            return {"status": "error", "error": str(e)}

"""Handler for security and compliance operations."""

from datetime import datetime
from typing import Any
import hashlib
import secrets

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityComplianceHandler:
    """Handler for security and compliance."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the security compliance handler."""
        self.client = client

    async def security_audit(self, user_id: str | None = None) -> dict[str, Any]:
        """Audit range for security best practices."""
        try:
            range_info = await self.client.get_range(user_id)
            range_config = await self.client.get_range_config(user_id)

            findings = []
            recommendations = []

            # Check for default passwords
            config_str = str(range_config).lower()
            if any(pwd in config_str for pwd in ["password", "123456", "admin"]):
                findings.append({
                    "severity": "high",
                    "category": "credentials",
                    "finding": "Potential default or weak passwords detected in configuration"
                })
                recommendations.append("Use strong, unique passwords for all VMs")

            # Check for unencrypted communications
            if "ssl: false" in config_str or "tls: false" in config_str:
                findings.append({
                    "severity": "medium",
                    "category": "encryption",
                    "finding": "Unencrypted communication channels detected"
                })
                recommendations.append("Enable SSL/TLS for all services")

            # Check testing state
            if range_info.get("testingEnabled"):
                findings.append({
                    "severity": "info",
                    "category": "exposure",
                    "finding": "Range has testing enabled (external access possible)"
                })
                recommendations.append("Disable testing when not actively conducting exercises")

            security_score = 100 - (len([f for f in findings if f["severity"] == "high"]) * 20) - (len([f for f in findings if f["severity"] == "medium"]) * 10)

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "security_score": max(0, security_score),
                "grade": self._score_to_grade(security_score),
                "findings": findings,
                "recommendations": recommendations,
                "summary": {
                    "high_severity": sum(1 for f in findings if f["severity"] == "high"),
                    "medium_severity": sum(1 for f in findings if f["severity"] == "medium"),
                    "low_severity": sum(1 for f in findings if f["severity"] == "low"),
                    "info": sum(1 for f in findings if f["severity"] == "info")
                }
            }
        except Exception as e:
            logger.error(f"Error performing security audit: {e}")
            return {"status": "error", "error": str(e)}

    async def compliance_check(
        self,
        framework: str = "general",
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Check compliance with organizational policies."""
        try:
            range_info = await self.client.get_range(user_id)

            compliance_results = {
                "framework": framework,
                "checks": [],
                "compliant": True
            }

            # Resource limits compliance
            vms = range_info.get("VMs", [])
            total_memory = sum(vm.get("memory", 0) for vm in vms) / 1024
            if total_memory > 64:
                compliance_results["checks"].append({
                    "control": "RESOURCE-001",
                    "description": "Memory usage under 64GB",
                    "status": "non_compliant",
                    "current_value": f"{total_memory:.2f} GB"
                })
                compliance_results["compliant"] = False
            else:
                compliance_results["checks"].append({
                    "control": "RESOURCE-001",
                    "description": "Memory usage under 64GB",
                    "status": "compliant",
                    "current_value": f"{total_memory:.2f} GB"
                })

            # Snapshot policy compliance
            try:
                snapshots = await self.client.list_snapshots(user_id)
                has_snapshots = len(snapshots) > 0 if snapshots else False
                compliance_results["checks"].append({
                    "control": "BACKUP-001",
                    "description": "Regular snapshots exist",
                    "status": "compliant" if has_snapshots else "non_compliant"
                })
                if not has_snapshots:
                    compliance_results["compliant"] = False
            except Exception as e:
                # Swallowing this used to drop the control from the report and
                # leave "compliant": True - claiming compliance for a check that
                # never ran. An unverifiable control is reported, not assumed.
                logger.warning(f"Snapshot compliance check failed: {e}")
                compliance_results["checks"].append({
                    "control": "BACKUP-001",
                    "description": "Regular snapshots exist",
                    "status": "unknown",
                    "error": str(e),
                })
                compliance_results["compliant"] = False

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "compliance_results": compliance_results,
                "overall_compliant": compliance_results["compliant"]
            }
        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            return {"status": "error", "error": str(e)}

    async def rotate_credentials(
        self,
        vm_names: list[str] | None = None,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """Bulk credential rotation for VMs."""
        try:
            range_info = await self.client.get_range(user_id)
            vms = range_info.get("VMs", [])

            if vm_names:
                vms = [vm for vm in vms if vm.get("name") in vm_names]

            rotations = []
            for vm in vms:
                new_password = self._generate_strong_password()
                rotations.append({
                    "vm_name": vm.get("name"),
                    "new_password": new_password,
                    "rotation_timestamp": datetime.now().isoformat(),
                    "note": "Apply using Ansible playbook: ansible.builtin.user module"
                })

            # NOTHING is applied here: this only generates candidate passwords.
            # Reporting "success" made callers believe the range had been
            # rotated when no machine was touched - a dangerous thing to get
            # wrong in a security tool.
            return {
                "status": "advisory",
                "applied": False,
                "warning": (
                    "No credentials were changed. These are SUGGESTED passwords; "
                    "apply them yourself with the guidance below."
                ),
                "timestamp": datetime.now().isoformat(),
                "suggested_credentials": rotations,
                "rotations": rotations,  # kept for backwards compatibility
                "vm_count": len(rotations),
                "implementation_guide": {
                    "ansible_playbook": "Use ansible.builtin.user with update_password: always",
                    "windows": "Use win_user module for Windows VMs"
                }
            }
        except Exception as e:
            logger.error(f"Error rotating credentials: {e}")
            return {"status": "error", "error": str(e)}

    async def get_vulnerability_scan(self, user_id: str | None = None) -> dict[str, Any]:
        """Integration point for vulnerability scanners."""
        try:
            range_info = await self.client.get_range(user_id)
            inventory = await self.client.get_range_ansible_inventory(user_id)

            vms = range_info.get("VMs", [])
            scan_targets = []

            for vm in vms:
                scan_targets.append({
                    "hostname": vm.get("name"),
                    "ip": vm.get("ip", "unknown"),
                    "os": vm.get("template", "unknown"),
                    "status": vm.get("status")
                })

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "scan_targets": scan_targets,
                "target_count": len(scan_targets),
                "integration_guide": {
                    "nessus": "Import targets into Nessus scanner",
                    "openvas": "Use targets for OpenVAS scan",
                    "ansible": "Use ansible community.general.nmap module"
                },
                "note": "This provides target information. Actual scanning requires external tools."
            }
        except Exception as e:
            logger.error(f"Error getting vulnerability scan info: {e}")
            return {"status": "error", "error": str(e)}

    def _generate_strong_password(self, length: int = 16) -> str:
        """Generate a strong random password."""
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _score_to_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 90: return "A"
        elif score >= 80: return "B"
        elif score >= 70: return "C"
        elif score >= 60: return "D"
        else: return "F"

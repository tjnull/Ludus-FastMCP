"""Handler for collaboration and sharing operations."""

from datetime import datetime
from typing import Any
import json
import hashlib
import base64

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class CollaborationHandler:
    """Handler for collaboration and sharing."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the collaboration handler."""
        self.client = client

    async def share_range_config(
        self,
        include_credentials: bool = False,
        expiry_hours: int = 24,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Generate shareable range configuration.

        Args:
            include_credentials: Whether to include credentials (use with caution)
            expiry_hours: Hours until share link expires
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with shareable configuration
        """
        try:
            range_config = await self.client.get_range_config(user_id)
            range_info = await self.client.get_range(user_id)

            # Sanitize configuration if credentials should not be included
            shared_config = json.loads(json.dumps(range_config))  # Deep copy

            if not include_credentials:
                # Remove sensitive fields
                self._sanitize_credentials(shared_config)

            # Generate share metadata
            share_id = hashlib.md5(
                f"{datetime.now()}{json.dumps(shared_config)}".encode()
            ).hexdigest()[:12]

            # Encode configuration
            config_json = json.dumps(shared_config, indent=2)
            config_base64 = base64.b64encode(config_json.encode()).decode()

            expiry_time = datetime.now().timestamp() + (expiry_hours * 3600)

            result = {
                "status": "success",
                "share_id": share_id,
                "created_at": datetime.now().isoformat(),
                "expires_at": datetime.fromtimestamp(expiry_time).isoformat(),
                "expires_in_hours": expiry_hours,
                "includes_credentials": include_credentials,
                "configuration": {
                    "raw": shared_config,
                    "base64": config_base64
                },
                "metadata": {
                    # "ludus" is a LIST of VMs and "network" is a top-level
                    # block; treating ludus as a dict raised
                    # "'list' object has no attribute 'get'" on every call.
                    "vm_count": len(shared_config.get("ludus") or []),
                    "network_count": len(
                        (shared_config.get("network") or {}).get("rules", [])
                    ),
                    "size_bytes": len(config_json)
                },
                "usage_instructions": {
                    "step_1": "Share the share_id and base64 configuration with collaborators",
                    "step_2": "Collaborators decode base64: echo '<base64>' | base64 -d > range_config.yml",
                    "step_3": "Import using: ludus.update_range_config with the decoded configuration",
                    "warning": "Never share configurations with credentials over insecure channels" if include_credentials else "Credentials have been removed for security"
                }
            }

            logger.info(f"Created shareable range config: {share_id}, {result['metadata']['vm_count']} VMs")
            return result

        except Exception as e:
            logger.error(f"Error creating shareable range config: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _sanitize_credentials(self, config: dict) -> None:
        """Remove sensitive information from configuration."""
        sensitive_fields = [
            "password", "passwd", "secret", "token", "key",
            "api_key", "apikey", "credential", "private_key"
        ]

        def sanitize_dict(d: dict) -> None:
            for key in list(d.keys()):
                if isinstance(d[key], dict):
                    sanitize_dict(d[key])
                elif isinstance(d[key], list):
                    for item in d[key]:
                        if isinstance(item, dict):
                            sanitize_dict(item)
                elif any(sensitive in key.lower() for sensitive in sensitive_fields):
                    d[key] = "***REDACTED***"

        sanitize_dict(config)

    async def import_community_scenario(
        self,
        scenario_source: str,
        scenario_name: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Import scenarios from community repository.

        Args:
            scenario_source: Source URL or base64 encoded scenario
            scenario_name: Name for the imported scenario
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with import result
        """
        try:
            # Determine source type
            if scenario_source.startswith("http://") or scenario_source.startswith("https://"):
                # URL source
                import_method = "url"
                scenario_data = {
                    "source_url": scenario_source,
                    "note": "Fetch scenario from URL and parse YAML/JSON"
                }
            else:
                # Assume base64 encoded
                import_method = "base64"
                try:
                    decoded = base64.b64decode(scenario_source)
                    scenario_data = json.loads(decoded)
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to decode scenario: {e}"
                    }

            # Validate scenario structure
            validation = self._validate_scenario_structure(scenario_data)
            if not validation["is_valid"]:
                return {
                    "status": "error",
                    "error": "Invalid scenario structure",
                    "validation": validation
                }

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "scenario_name": scenario_name,
                "import_method": import_method,
                "scenario_data": scenario_data,
                "validation": validation,
                "next_steps": {
                    "step_1": "Review the scenario_data",
                    "step_2": "Use ludus.deploy_scenario to deploy",
                    "step_3": "Or save to scenarios/ directory for permanent use"
                }
            }

            logger.info(f"Imported community scenario: {scenario_name} via {import_method}")
            return result

        except Exception as e:
            logger.error(f"Error importing community scenario: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _validate_scenario_structure(self, scenario: dict) -> dict[str, Any]:
        """Validate scenario structure."""
        errors = []
        warnings = []

        # Check for required sections
        if "ludus" not in scenario:
            errors.append("Missing 'ludus' section")

        if "ludus" in scenario:
            ludus_section = scenario["ludus"]
            if "vms" not in ludus_section:
                errors.append("Missing 'vms' in ludus section")

        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }

    async def publish_scenario(
        self,
        scenario_name: str,
        description: str,
        tags: list[str] | None = None,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Share custom scenarios with community.

        Args:
            scenario_name: Name of scenario to publish
            description: Scenario description
            tags: Optional tags for categorization
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with publication result
        """
        try:
            # Get current range configuration as scenario
            range_config = await self.client.get_range_config(user_id)
            range_info = await self.client.get_range(user_id)

            # Create sanitized scenario package
            sanitized_config = json.loads(json.dumps(range_config))
            self._sanitize_credentials(sanitized_config)

            # Create scenario metadata
            scenario_package = {
                "name": scenario_name,
                "description": description,
                "author": "ludus-user",
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
                "tags": tags or [],
                "statistics": {
                    "vm_count": len(sanitized_config.get("ludus", {}).get("vms", [])),
                    "network_count": len(sanitized_config.get("ludus", {}).get("network", []))
                },
                "configuration": sanitized_config
            }

            # Encode for sharing
            package_json = json.dumps(scenario_package, indent=2)
            package_base64 = base64.b64encode(package_json.encode()).decode()

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "scenario_name": scenario_name,
                "package": scenario_package,
                "encoded_package": package_base64,
                "publish_instructions": {
                    "github": "Create a PR to ludus-scenarios repository with this scenario",
                    "share": "Share the encoded_package with others",
                    "import": "Others can use ludus.import_community_scenario with this package"
                },
                "metadata": {
                    "size_bytes": len(package_json),
                    "vm_count": scenario_package["statistics"]["vm_count"]
                }
            }

            logger.info(f"Published scenario: {scenario_name}, {result['metadata']['vm_count']} VMs")
            return result

        except Exception as e:
            logger.error(f"Error publishing scenario: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def range_access_logs(
        self,
        days: int = 7,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        View who accessed the range and when.

        Args:
            days: Number of days to look back
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with access logs
        """
        try:
            # Get range access information
            try:
                access_info = await self.client.get_range_access(user_id)
            except Exception:
                access_info = []

            # Simulate access log analysis
            # In a real implementation, this would query actual access logs
            access_logs = []

            if access_info:
                for access in access_info:
                    access_logs.append({
                        "user_id": access.get("userId", "unknown"),
                        "user_name": access.get("userName", "unknown"),
                        "access_level": access.get("accessLevel", "unknown"),
                        "granted_at": access.get("grantedAt", datetime.now().isoformat()),
                        "last_seen": "N/A - tracking not implemented"
                    })

            # Generate statistics
            unique_users = len(set(log["user_id"] for log in access_logs))

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "lookback_days": days,
                "access_logs": access_logs,
                "statistics": {
                    "total_accesses": len(access_logs),
                    "unique_users": unique_users,
                    "current_users_with_access": len(access_info) if access_info else 0
                },
                "note": "This shows current access permissions. Full access logging requires external logging system."
            }

            logger.info(f"Retrieved access logs: {unique_users} unique users")
            return result

        except Exception as e:
            logger.error(f"Error getting access logs: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

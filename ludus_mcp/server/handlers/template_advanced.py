"""Handler for advanced template management operations."""

from datetime import datetime
from typing import Any
import json
import difflib

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateAdvancedHandler:
    """Handler for advanced template management."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the template advanced handler."""
        self.client = client

    async def template_diff(
        self,
        template1: str,
        template2: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Compare two template configurations.

        Args:
            template1: First template name or ID
            template2: Second template name or ID
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with comparison results
        """
        try:
            # Get both template configurations
            templates = await self.client.list_templates()

            t1 = next((t for t in templates if t.get("name") == template1 or t.get("id") == template1), None)
            t2 = next((t for t in templates if t.get("name") == template2 or t.get("id") == template2), None)

            if not t1:
                return {"status": "error", "error": f"Template not found: {template1}"}
            if not t2:
                return {"status": "error", "error": f"Template not found: {template2}"}

            # Convert to JSON strings for comparison
            t1_json = json.dumps(t1, indent=2, sort_keys=True)
            t2_json = json.dumps(t2, indent=2, sort_keys=True)

            # Generate unified diff
            diff_lines = list(difflib.unified_diff(
                t1_json.splitlines(keepends=True),
                t2_json.splitlines(keepends=True),
                fromfile=template1,
                tofile=template2,
                lineterm=''
            ))

            # Analyze differences
            differences = self._analyze_template_differences(t1, t2)

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "template1": {
                    "name": t1.get("name"),
                    "id": t1.get("id"),
                    "type": t1.get("type", "unknown")
                },
                "template2": {
                    "name": t2.get("name"),
                    "id": t2.get("id"),
                    "type": t2.get("type", "unknown")
                },
                "differences": differences,
                "unified_diff": ''.join(diff_lines),
                "identical": len(differences) == 0
            }

            logger.info(f"Template diff: {template1} vs {template2}, {len(differences)} differences")
            return result

        except Exception as e:
            logger.error(f"Error comparing templates: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _analyze_template_differences(self, t1: dict, t2: dict) -> list[dict]:
        """Analyze specific differences between templates."""
        differences = []

        # Compare common fields
        fields_to_compare = ["name", "type", "version", "description", "os", "architecture"]

        for field in fields_to_compare:
            v1 = t1.get(field)
            v2 = t2.get(field)
            if v1 != v2:
                differences.append({
                    "field": field,
                    "template1_value": v1,
                    "template2_value": v2,
                    "type": "field_difference"
                })

        # Check for unique keys
        keys1 = set(t1.keys())
        keys2 = set(t2.keys())

        only_in_t1 = keys1 - keys2
        only_in_t2 = keys2 - keys1

        if only_in_t1:
            differences.append({
                "type": "unique_keys",
                "template": "template1",
                "keys": list(only_in_t1)
            })

        if only_in_t2:
            differences.append({
                "type": "unique_keys",
                "template": "template2",
                "keys": list(only_in_t2)
            })

        return differences

    async def validate_template(
        self,
        template_config: dict,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Validate template configuration before building.

        Args:
            template_config: Template configuration to validate
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with validation results
        """
        try:
            errors = []
            warnings = []
            suggestions = []

            # Required fields validation
            required_fields = ["name", "type"]
            for field in required_fields:
                if field not in template_config:
                    errors.append({
                        "severity": "error",
                        "field": field,
                        "message": f"Required field '{field}' is missing"
                    })

            # Name validation
            if "name" in template_config:
                name = template_config["name"]
                if not isinstance(name, str) or len(name) < 3:
                    errors.append({
                        "severity": "error",
                        "field": "name",
                        "message": "Template name must be at least 3 characters"
                    })
                if " " in name:
                    warnings.append({
                        "severity": "warning",
                        "field": "name",
                        "message": "Template name contains spaces, consider using hyphens"
                    })

            # Type validation
            valid_types = ["vm", "container", "custom"]
            if "type" in template_config:
                if template_config["type"] not in valid_types:
                    warnings.append({
                        "severity": "warning",
                        "field": "type",
                        "message": f"Unexpected template type. Common types: {valid_types}"
                    })

            # Resource validation
            if "resources" in template_config:
                resources = template_config["resources"]
                if isinstance(resources, dict):
                    # Memory check
                    if "memory" in resources:
                        memory = resources["memory"]
                        if memory < 512:
                            warnings.append({
                                "severity": "warning",
                                "field": "resources.memory",
                                "message": "Memory less than 512MB may cause issues"
                            })
                        if memory > 32768:
                            warnings.append({
                                "severity": "warning",
                                "field": "resources.memory",
                                "message": "Very high memory allocation (>32GB)"
                            })

                    # CPU check
                    if "cpus" in resources:
                        cpus = resources["cpus"]
                        if cpus < 1:
                            errors.append({
                                "severity": "error",
                                "field": "resources.cpus",
                                "message": "At least 1 CPU required"
                            })
                        if cpus > 16:
                            warnings.append({
                                "severity": "warning",
                                "field": "resources.cpus",
                                "message": "Very high CPU allocation (>16 cores)"
                            })

            # Suggestions
            if "description" not in template_config:
                suggestions.append("Add a description field to document the template purpose")

            if "version" not in template_config:
                suggestions.append("Add a version field for better template tracking")

            # Overall validation result
            is_valid = len(errors) == 0
            validation_level = "valid" if is_valid else "invalid"
            if is_valid and warnings:
                validation_level = "valid_with_warnings"

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "validation_result": validation_level,
                "is_valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "summary": {
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "suggestion_count": len(suggestions)
                }
            }

            logger.info(f"Template validation: {validation_level}, {len(errors)} errors, {len(warnings)} warnings")
            return result

        except Exception as e:
            logger.error(f"Error validating template: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_template_dependencies(
        self,
        template_name: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        List required roles and collections for a template.

        Args:
            template_name: Template name or ID
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with template dependencies
        """
        try:
            templates = await self.client.list_templates()
            template = next((t for t in templates if t.get("name") == template_name or t.get("id") == template_name), None)

            if not template:
                return {
                    "status": "error",
                    "error": f"Template not found: {template_name}"
                }

            # Extract dependencies from template configuration
            dependencies = {
                "ansible_roles": [],
                "ansible_collections": [],
                "system_packages": [],
                "custom_scripts": []
            }

            # Parse template for common Ludus roles
            template_str = json.dumps(template).lower()

            # Common Ludus roles
            common_roles = [
                "ludus_ad",
                "ludus_dc",
                "ludus_domain_user",
                "ludus_windows",
                "ludus_linux",
                "badsecrets",
                "geerlingguy.docker",
                "geerlingguy.postgresql"
            ]

            for role in common_roles:
                if role.lower() in template_str:
                    dependencies["ansible_roles"].append(role)

            # Common collections
            if "community" in template_str:
                dependencies["ansible_collections"].append("community.general")
            if "ansible.windows" in template_str:
                dependencies["ansible_collections"].append("ansible.windows")

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "template": {
                    "name": template.get("name"),
                    "id": template.get("id"),
                    "type": template.get("type")
                },
                "dependencies": dependencies,
                "installation_commands": self._generate_installation_commands(dependencies),
                "note": "This is an estimated dependency list based on template analysis"
            }

            logger.info(f"Template dependencies for {template_name}: {len(dependencies['ansible_roles'])} roles")
            return result

        except Exception as e:
            logger.error(f"Error getting template dependencies: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_installation_commands(self, dependencies: dict) -> dict[str, list[str]]:
        """Generate installation commands for dependencies."""
        commands = {
            "ansible_galaxy": [],
            "package_manager": []
        }

        # Ansible roles
        for role in dependencies.get("ansible_roles", []):
            commands["ansible_galaxy"].append(f"ansible-galaxy role install {role}")

        # Ansible collections
        for collection in dependencies.get("ansible_collections", []):
            commands["ansible_galaxy"].append(f"ansible-galaxy collection install {collection}")

        # System packages
        for package in dependencies.get("system_packages", []):
            commands["package_manager"].append(f"apt install {package}  # or yum/dnf")

        return commands

    async def optimize_template(
        self,
        template_name: str,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Suggest optimizations for template configuration.

        Args:
            template_name: Template name or ID
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with optimization suggestions
        """
        try:
            templates = await self.client.list_templates()
            template = next((t for t in templates if t.get("name") == template_name or t.get("id") == template_name), None)

            if not template:
                return {
                    "status": "error",
                    "error": f"Template not found: {template_name}"
                }

            optimizations = []
            potential_savings = {
                "memory_mb": 0,
                "cpus": 0,
                "disk_gb": 0
            }

            # Analyze template configuration
            template_type = template.get("type", "unknown")

            # Memory optimization
            if "memory" in template:
                memory = template["memory"]
                if memory > 8192:
                    optimizations.append({
                        "category": "memory",
                        "priority": "medium",
                        "suggestion": f"Memory allocation of {memory}MB is quite high. Consider if full amount is needed.",
                        "current_value": memory,
                        "suggested_value": 8192,
                        "potential_savings_mb": memory - 8192
                    })
                    potential_savings["memory_mb"] = memory - 8192

            # CPU optimization
            if "cpus" in template:
                cpus = template["cpus"]
                if cpus > 4:
                    optimizations.append({
                        "category": "cpu",
                        "priority": "medium",
                        "suggestion": f"CPU allocation of {cpus} cores is high. Most VMs work well with 2-4 cores.",
                        "current_value": cpus,
                        "suggested_value": 4,
                        "potential_savings_cpus": cpus - 4
                    })
                    potential_savings["cpus"] = cpus - 4

            # Disk optimization
            if "disk" in template:
                disk = template["disk"]
                if disk > 100:
                    optimizations.append({
                        "category": "disk",
                        "priority": "low",
                        "suggestion": f"Disk allocation of {disk}GB is large. Consider if full space is needed.",
                        "current_value": disk,
                        "suggested_value": 80,
                        "potential_savings_gb": disk - 80
                    })
                    potential_savings["disk_gb"] = disk - 80

            # Performance optimizations
            optimizations.append({
                "category": "performance",
                "priority": "high",
                "suggestion": "Enable disk caching for better I/O performance",
                "implementation": "Add 'cache_mode: writeback' to disk configuration"
            })

            optimizations.append({
                "category": "performance",
                "priority": "medium",
                "suggestion": "Use VirtIO drivers for better network performance",
                "implementation": "Ensure VirtIO drivers are installed in the VM"
            })

            # Security optimizations
            optimizations.append({
                "category": "security",
                "priority": "high",
                "suggestion": "Ensure template uses latest OS version",
                "implementation": "Update base image to latest stable release"
            })

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "template": {
                    "name": template.get("name"),
                    "id": template.get("id"),
                    "type": template_type
                },
                "optimizations": optimizations,
                "potential_savings": potential_savings,
                "summary": {
                    "total_suggestions": len(optimizations),
                    "high_priority": sum(1 for o in optimizations if o.get("priority") == "high"),
                    "medium_priority": sum(1 for o in optimizations if o.get("priority") == "medium"),
                    "low_priority": sum(1 for o in optimizations if o.get("priority") == "low")
                }
            }

            logger.info(f"Template optimization for {template_name}: {len(optimizations)} suggestions")
            return result

        except Exception as e:
            logger.error(f"Error optimizing template: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

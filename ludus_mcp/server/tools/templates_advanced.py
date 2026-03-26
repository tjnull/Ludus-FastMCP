"""Advanced template FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.template_advanced import TemplateAdvancedHandler
from ludus_mcp.server.handlers.template_builder import TemplateBuilder
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response
from ludus_mcp.utils.version_guard import require_v2


def create_template_advanced_tools(client: LudusAPIClient) -> FastMCP:
    """Create advanced template tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with advanced template tools registered
    """
    mcp = FastMCP("Advanced Templates")
    registry = LazyHandlerRegistry(client)

    # ==================== TEMPLATE MANAGEMENT TOOLS ====================

    @mcp.tool()
    async def add_template(
        name: str,
        url: str,
        description: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Add a new template to the system.

        Args:
            name: Template name
            url: Template URL or image source
            description: Optional template description
            user_id: Optional user ID (admin only)

        Returns:
            Template addition result
        """
        result = await client.add_template(name, url, description, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def build_template(
        template_id: str,
        force: bool = False,
        user_id: str | None = None
    ) -> dict:
        """Build a template.

        Args:
            template_id: Template ID to build
            force: Force rebuild even if template exists
            user_id: Optional user ID (admin only)

        Returns:
            Build initiation result
        """
        result = await client.build_template(template_id, force, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def delete_template(
        template_id: str,
        user_id: str | None = None
    ) -> dict:
        """Delete a template.

        Args:
            template_id: Template ID to delete
            user_id: Optional user ID (admin only)

        Returns:
            Deletion result
        """
        result = await client.delete_template(template_id, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_template_status(
        template_id: str,
        user_id: str | None = None
    ) -> dict:
        """Get template build status.

        Args:
            template_id: Template ID
            user_id: Optional user ID (admin only)

        Returns:
            Template build status
        """
        result = await client.get_template_status(template_id, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_template_logs(
        template_id: str,
        user_id: str | None = None
    ) -> str:
        """Get template build logs.

        Args:
            template_id: Template ID
            user_id: Optional user ID (admin only)

        Returns:
            Template build logs
        """
        result = await client.get_template_logs(template_id, user_id)
        return result

    @mcp.tool()
    async def abort_template_build(
        template_id: str,
        user_id: str | None = None
    ) -> dict:
        """Abort a template build.

        Args:
            template_id: Template ID
            user_id: Optional user ID (admin only)

        Returns:
            Abort result
        """
        result = await client.abort_template_build(template_id, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def apply_template(
        vm_name: str,
        template_id: str,
        user_id: str | None = None
    ) -> dict:
        """Apply a template to a VM.

        Args:
            vm_name: Name of the VM to apply template to
            template_id: Template ID to apply
            user_id: Optional user ID (admin only)

        Returns:
            Template application result
        """
        handler = registry.get_handler("template_advanced", TemplateAdvancedHandler)
        result = await handler.apply_template(vm_name, template_id, user_id)
        return format_tool_response(result)

    # ==================== TEMPLATE BUILDER TOOLS ====================

    @mcp.tool()
    async def create_custom_template(
        name: str,
        os_type: str,
        os_version: str | None = None,
        packages: list[str] | None = None,
        containers: list[dict[str, Any]] | None = None,
        description: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Create a custom template from scratch.

        Args:
            name: Name for the custom template
            os_type: OS type (linux, windows)
            os_version: OS version (e.g., "22.04", "2022")
            packages: List of packages to install
            containers: List of container configurations
            description: Optional description
            user_id: Optional user ID (admin only)

        Returns:
            Custom template creation result
        """
        builder = TemplateBuilder()
        result = builder.create_template(
            name=name,
            os_type=os_type,
            os_version=os_version,
            packages=packages,
            containers=containers,
            description=description
        )
        return format_tool_response(result)

    @mcp.tool()
    async def create_container_template(
        name: str,
        base_os: str,
        containers: list[dict[str, Any]],
        description: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Create a container-based template.

        Args:
            name: Name for the container template
            base_os: Base OS (e.g., "ubuntu-22.04", "debian-12")
            containers: List of container configurations
            description: Optional description
            user_id: Optional user ID (admin only)

        Returns:
            Container template creation result
        """
        builder = TemplateBuilder()
        result = builder.create_container_template(
            name=name,
            base_os=base_os,
            containers=containers,
            description=description
        )
        return format_tool_response(result)

    @mcp.tool()
    async def list_common_containers() -> dict[str, dict]:
        """List common container base images.

        Returns:
            Dictionary of common container configurations
        """
        builder = TemplateBuilder()
        result = builder.get_common_container_configs()
        return result

    @mcp.tool()
    async def get_container_config(container_name: str) -> dict:
        """Get configuration for a common container.

        Args:
            container_name: Container name

        Returns:
            Container configuration
        """
        builder = TemplateBuilder()
        configs = builder.get_common_container_configs()
        if container_name in configs:
            return configs[container_name]
        return {"error": f"Container '{container_name}' not found", "available": list(configs.keys())}

    @mcp.tool()
    async def template_diff(
        template_id1: str,
        template_id2: str,
        user_id: str | None = None
    ) -> dict:
        """Compare two templates and show differences.

        Args:
            template_id1: First template ID
            template_id2: Second template ID
            user_id: Optional user ID (admin only)

        Returns:
            Template differences
        """
        handler = registry.get_handler("template_advanced", TemplateAdvancedHandler)
        result = await handler.template_diff(template_id1, template_id2, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def validate_template(
        template_config: dict[str, Any],
        user_id: str | None = None
    ) -> dict:
        """Validate a template configuration.

        Args:
            template_config: Template configuration to validate
            user_id: Optional user ID (admin only)

        Returns:
            Validation result with errors and warnings
        """
        handler = registry.get_handler("template_advanced", TemplateAdvancedHandler)
        result = await handler.validate_template(template_config, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_template_dependencies(
        template_id: str,
        user_id: str | None = None
    ) -> list[dict]:
        """Get template dependencies.

        Args:
            template_id: Template ID
            user_id: Optional user ID (admin only)

        Returns:
            List of template dependencies
        """
        handler = registry.get_handler("template_advanced", TemplateAdvancedHandler)
        result = await handler.get_template_dependencies(template_id, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def optimize_template(
        template_id: str,
        user_id: str | None = None
    ) -> dict:
        """Optimize a template for better performance.

        Args:
            template_id: Template ID to optimize
            user_id: Optional user ID (admin only)

        Returns:
            Optimization result
        """
        handler = registry.get_handler("template_advanced", TemplateAdvancedHandler)
        result = await handler.optimize_template(template_id, user_id)
        return format_tool_response(result)

    # ==================== ANSIBLE V2 TOOLS ====================

    @mcp.tool()
    async def move_ansible_role_scope(role_name: str, scope: str) -> dict:
        """Move an Ansible role's scope (Ludus 2.0 only).

        Args:
            role_name: Name of the role to move
            scope: New scope for the role

        Returns:
            Move result
        """
        guard = require_v2(client, "Ansible Role Scope Management")
        if guard:
            return guard
        result = await client.move_role_scope(role_name, scope)
        return format_tool_response(result)

    @mcp.tool()
    async def get_ansible_role_vars(role_name: str) -> dict:
        """Get variables for an Ansible role (Ludus 2.0 only).

        Args:
            role_name: Name of the role

        Returns:
            Role variables
        """
        guard = require_v2(client, "Ansible Role Variables")
        if guard:
            return guard
        result = await client.get_role_vars(role_name)
        return format_tool_response(result)

    @mcp.tool()
    async def list_subscription_roles() -> list[dict]:
        """List available subscription roles (Ludus 2.0 Enterprise only).

        Returns:
            List of subscription roles
        """
        guard = require_v2(client, "Subscription Roles")
        if guard:
            return guard
        result = await client.list_subscription_roles()
        return format_tool_response(result)

    @mcp.tool()
    async def install_subscription_roles(roles: list[str]) -> dict:
        """Install subscription roles (Ludus 2.0 Enterprise only).

        Args:
            roles: List of role names to install

        Returns:
            Installation result
        """
        guard = require_v2(client, "Subscription Roles")
        if guard:
            return guard
        result = await client.install_subscription_roles(roles)
        return format_tool_response(result)

    return mcp

"""Documentation generation FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.documentation import DocumentationHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_documentation_tools(client: LudusAPIClient) -> FastMCP:
    """Create documentation generation tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with documentation tools registered
    """
    mcp = FastMCP("Documentation")
    registry = LazyHandlerRegistry(client)

    # ==================== DOCUMENTATION GENERATION TOOLS ====================

    @mcp.tool()
    async def generate_range_documentation(
        format: str = "markdown",
        include_credentials: bool = False,
        user_id: str | None = None
    ) -> dict:
        """Generate comprehensive documentation for the range.

        Args:
            format: Documentation format (markdown, html, pdf)
            include_credentials: Include credentials in documentation
            user_id: Optional user ID (admin only)

        Returns:
            Documentation content
        """
        handler = registry.get_handler("documentation", DocumentationHandler)
        result = await handler.generate_range_documentation(
            format=format, include_credentials=include_credentials, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def get_attack_path_documentation(
        scenario_key: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Generate attack path documentation for an attack technique.

        Note that scenario_key names an attack technique ("kerberoasting",
        "golden-ticket"), not a range scenario like "redteam-lab-lite". There is
        no default: omitting it returns the list of techniques available.

        Args:
            scenario_key: Attack technique to document
            user_id: Optional user ID (admin only)

        Returns:
            Attack path documentation with techniques and mitigations, or the
            list of available techniques if scenario_key is missing or unknown
        """
        handler = registry.get_handler("documentation", DocumentationHandler)
        result = await handler.get_attack_path_documentation(scenario_key, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def export_lab_guide(
        title: str = "Lab Guide",
        difficulty: str = "intermediate",
        user_id: str | None = None
    ) -> dict:
        """Export lab guide for training purposes.

        The guide is generated from the current range deployment.

        Args:
            title: Title for the generated lab guide
            difficulty: Difficulty level (beginner, intermediate, advanced)
            user_id: Optional user ID (admin only)

        Returns:
            Lab guide content
        """
        handler = registry.get_handler("documentation", DocumentationHandler)
        result = await handler.export_lab_guide(
            title=title, difficulty=difficulty, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def create_scenario_playbook(
        scenario_name: str,
        team: str = "red",
        user_id: str | None = None
    ) -> dict:
        """Generate a red or blue team playbook for a scenario.

        Args:
            scenario_name: Name of the scenario the playbook is for
            team: Which team the playbook is written for (red, blue)
            user_id: Optional user ID (admin only)

        Returns:
            Generated playbook
        """
        handler = registry.get_handler("documentation", DocumentationHandler)
        result = await handler.create_scenario_playbook(
            scenario_name=scenario_name, team=team, user_id=user_id
        )
        return format_tool_response(result)

    return mcp

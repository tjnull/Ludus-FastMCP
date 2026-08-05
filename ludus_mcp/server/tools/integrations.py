"""Integration FastMCP tools for Ludus MCP server - webhooks, Slack, Jira, Git."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.integrations import IntegrationsHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_integration_tools(client: LudusAPIClient) -> FastMCP:
    """Create integration tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with integration tools registered
    """
    mcp = FastMCP("Integrations")
    registry = LazyHandlerRegistry(client)

    # ==================== WEBHOOK INTEGRATION ====================

    @mcp.tool()
    async def webhook_integration(
        webhook_url: str,
        events: list[str],
        secret: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Configure a webhook for range events.

        Args:
            webhook_url: URL to POST events to
            events: List of events that should trigger the webhook
            secret: Optional shared secret used to sign deliveries
            user_id: Optional user ID (admin only)

        Returns:
            Webhook configuration result
        """
        handler = registry.get_handler("integration", IntegrationsHandler)
        result = await handler.webhook_integration(
            webhook_url=webhook_url, events=events, secret=secret, user_id=user_id
        )
        return format_tool_response(result)

    # ==================== SLACK INTEGRATION ====================

    @mcp.tool()
    async def slack_notifications(
        webhook_url: str,
        channel: str,
        notification_types: list[str],
        user_id: str | None = None
    ) -> dict:
        """Configure Slack notifications for deployment status.

        Args:
            webhook_url: Slack incoming webhook URL
            channel: Slack channel to post to
            notification_types: Event types to notify on
            user_id: Optional user ID (admin only)

        Returns:
            Slack integration result
        """
        handler = registry.get_handler("integration", IntegrationsHandler)
        result = await handler.slack_notifications(
            webhook_url=webhook_url, channel=channel,
            notification_types=notification_types, user_id=user_id
        )
        return format_tool_response(result)

    # ==================== JIRA INTEGRATION ====================

    @mcp.tool()
    async def jira_integration(
        jira_url: str,
        project_key: str,
        api_token: str,
        issue_types: dict[str, str] | None = None,
        user_id: str | None = None
    ) -> dict:
        """Configure JIRA issue creation for failed deployments.

        Args:
            jira_url: Jira instance URL
            project_key: Jira project key
            api_token: Jira API token
            issue_types: Optional mapping of event type to Jira issue type
            user_id: Optional user ID (admin only)

        Returns:
            Jira integration result
        """
        handler = registry.get_handler("integration", IntegrationsHandler)
        result = await handler.jira_integration(
            jira_url=jira_url, project_key=project_key, api_token=api_token,
            issue_types=issue_types, user_id=user_id
        )
        return format_tool_response(result)

    # ==================== GIT SYNC ====================

    @mcp.tool()
    async def git_sync(
        repo_url: str,
        branch: str = "main",
        auto_commit: bool = True,
        user_id: str | None = None
    ) -> dict:
        """Sync range configurations with a Git repository.

        Args:
            repo_url: Git repository URL
            branch: Git branch to sync with
            auto_commit: Commit configuration changes automatically
            user_id: Optional user ID (admin only)

        Returns:
            Git sync result
        """
        handler = registry.get_handler("integration", IntegrationsHandler)
        result = await handler.git_sync(
            repo_url=repo_url, branch=branch, auto_commit=auto_commit, user_id=user_id
        )
        return format_tool_response(result)

    return mcp

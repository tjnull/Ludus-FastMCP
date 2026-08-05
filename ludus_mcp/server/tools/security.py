"""Security and SIEM FastMCP tools for Ludus MCP server."""

from typing import Any
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.siem import SIEMHandler
from ludus_mcp.server.handlers.wazuh import WazuhHandler
from ludus_mcp.server.handlers.access import AccessHandler
from ludus_mcp.server.handlers.security_compliance import SecurityComplianceHandler
from ludus_mcp.server.handlers.collaboration import CollaborationHandler
from ludus_mcp.server.tools.utils import LazyHandlerRegistry, format_tool_response


def create_security_tools(client: LudusAPIClient) -> FastMCP:
    """Create security and SIEM tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with security tools registered
    """
    mcp = FastMCP("Security & SIEM")
    registry = LazyHandlerRegistry(client)

    # ==================== SIEM TOOLS ====================

    @mcp.tool()
    async def get_siem_info(user_id: str | None = None) -> dict:
        """Get SIEM information for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            SIEM configuration and status
        """
        handler = registry.get_handler("siem", SIEMHandler)
        result = await handler.get_siem_server_info(user_id=user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_siem_alerts(
        siem_type: str = "wazuh",
        limit: int = 100,
        severity: str | None = None,
        user_id: str | None = None
    ) -> dict:
        """Get SIEM alerts for the range.

        Args:
            siem_type: SIEM platform to query (wazuh, splunk, elastic, security-onion)
            limit: Maximum number of alerts to return
            severity: Filter by severity level (low, medium, high, critical)
            user_id: Optional user ID (admin only)

        Returns:
            SIEM alerts
        """
        handler = registry.get_handler("siem", SIEMHandler)
        result = await handler.get_siem_alerts(
            siem_type=siem_type, limit=limit, severity=severity, user_id=user_id
        )
        return format_tool_response(result)

    @mcp.tool()
    async def get_siem_agents(user_id: str | None = None) -> dict:
        """Get SIEM agents for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            List of SIEM agents
        """
        handler = registry.get_handler("siem", SIEMHandler)
        result = await handler.get_siem_agents_status(user_id=user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_detection_summary(
        siem_type: str = "wazuh",
        user_id: str | None = None
    ) -> dict:
        """Get detection summary from SIEM.

        Args:
            siem_type: SIEM platform to query (wazuh, splunk, elastic, security-onion)
            user_id: Optional user ID (admin only)

        Returns:
            Detection summary with statistics
        """
        handler = registry.get_handler("siem", SIEMHandler)
        result = await handler.get_detection_summary(siem_type=siem_type, user_id=user_id)
        return format_tool_response(result)

    # ==================== WAZUH TOOLS ====================

    @mcp.tool()
    async def get_wazuh_info(user_id: str | None = None) -> dict:
        """Get Wazuh SIEM information for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Wazuh configuration and status
        """
        handler = registry.get_handler("wazuh", WazuhHandler)
        result = await handler.get_wazuh_server_info(user_id=user_id)
        return format_tool_response(result)

    # ==================== ACCESS CONTROL TOOLS ====================

    @mcp.tool()
    async def get_range_access(user_id: str | None = None) -> list | dict:
        """Get range access information.

        Returns the LIST of ranges the caller can access, which may be empty.
        To see who can access a specific range, use list_range_users instead.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Ranges the caller can access
        """
        handler = registry.get_handler("access", AccessHandler)
        result = await handler.get_range_access(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def grant_range_access(
        users: list[str],
        user_id: str | None = None
    ) -> dict:
        """Grant other users access to your range.

        Ludus grants range access per user; there are no per-permission levels.

        Args:
            users: List of user IDs to grant access to
            user_id: Range owner user ID (admin only)

        Returns:
            Updated access configuration
        """
        handler = registry.get_handler("access", AccessHandler)
        result = await handler.grant_range_access(users=users, user_id=user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def revoke_range_access(
        target_user_id: str,
        user_id: str | None = None
    ) -> dict:
        """Revoke range access from a user.

        Args:
            target_user_id: User ID to revoke access from
            user_id: Optional user ID (admin only)

        Returns:
            Revoke result
        """
        handler = registry.get_handler("access", AccessHandler)
        result = await handler.revoke_range_access(target_user_id, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def clear_range_access(user_id: str | None = None) -> dict:
        """Clear all range access permissions.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Clear result
        """
        handler = registry.get_handler("access", AccessHandler)
        result = await handler.clear_range_access(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def range_access_logs(
        days: int = 7,
        user_id: str | None = None
    ) -> dict:
        """Get range access logs.

        Args:
            days: Number of days of history to look back
            user_id: Optional user ID (admin only)

        Returns:
            List of access log entries
        """
        handler = registry.get_handler("collaboration", CollaborationHandler)
        result = await handler.range_access_logs(days=days, user_id=user_id)
        return format_tool_response(result)

    # ==================== SECURITY COMPLIANCE TOOLS ====================

    @mcp.tool()
    async def security_audit(user_id: str | None = None) -> dict:
        """Run security audit on the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Security audit report
        """
        handler = registry.get_handler("security_compliance", SecurityComplianceHandler)
        result = await handler.security_audit(user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def compliance_check(
        framework: str = "nist",
        user_id: str | None = None
    ) -> dict:
        """Check compliance against security framework.

        Args:
            framework: Security framework to check against (nist, pci, iso27001)
            user_id: Optional user ID (admin only)

        Returns:
            Compliance check results
        """
        handler = registry.get_handler("security_compliance", SecurityComplianceHandler)
        result = await handler.compliance_check(framework, user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def rotate_credentials(
        vm_names: list[str] | None = None,
        user_id: str | None = None
    ) -> dict:
        """Suggest new credentials for VMs in the range. DOES NOT APPLY THEM.

        Ludus exposes no API for setting VM user passwords, so this only
        generates strong candidates and explains how to apply them with
        Ansible. Nothing on any machine is changed. Do not report to a user
        that credentials have been rotated based on this tool's output.

        Args:
            vm_names: VMs to generate credentials for (omit for every VM)
            user_id: Optional user ID (admin only)

        Returns:
            Suggested credentials plus guidance for applying them
        """
        handler = registry.get_handler("security_compliance", SecurityComplianceHandler)
        result = await handler.rotate_credentials(vm_names=vm_names, user_id=user_id)
        return format_tool_response(result)

    @mcp.tool()
    async def get_vulnerability_scan(user_id: str | None = None) -> dict:
        """Get vulnerability scan results for the range.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Vulnerability scan results
        """
        handler = registry.get_handler("security_compliance", SecurityComplianceHandler)
        result = await handler.get_vulnerability_scan(user_id)
        return format_tool_response(result)

    return mcp

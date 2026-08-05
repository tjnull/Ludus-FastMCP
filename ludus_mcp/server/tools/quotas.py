"""Quota, auto-shutdown and deployment-history tools (Ludus 2.0+ only).

Quotas cap what a user or group may consume. Auto-shutdown powers idle ranges
off so they stop burning host resources. Log history exposes previous
deployments and template builds, not just the one currently running.
"""

from typing import Any, Awaitable
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.exceptions import LudusNotFoundError
from ludus_mcp.server.tools.utils import format_tool_response
from ludus_mcp.utils.version_guard import require_v2


async def _call(feature: str, coro: Awaitable[Any]) -> Any:
    """Run a plugin-backed call, turning "plugin not loaded" into a clear answer.

    Quotas and auto-shutdown are served by Ludus plugins. On a server without
    them the API returns 404, which otherwise surfaces as "not found" and reads
    like a broken path rather than an absent feature.
    """
    try:
        return format_tool_response(await coro)
    except LudusNotFoundError as e:
        if "plugin" not in str(e).lower():
            raise
        return {
            "available": False,
            "feature": feature,
            "error": f"{feature} is not available on this Ludus server.",
            "reason": (
                "This capability is provided by a Ludus plugin that is not loaded "
                "on the server (typically an enterprise feature)."
            ),
            "hint": (
                "The request was well-formed. Do not retry or try alternative "
                "endpoints -- the server does not implement this feature."
            ),
        }


def create_quota_tools(client: LudusAPIClient) -> FastMCP:
    """Create quota, auto-shutdown and log-history tools.

    Args:
        client: Ludus API client

    Returns:
        FastMCP instance with the tools registered
    """
    mcp = FastMCP("Quotas & Limits")

    # ---------- Quotas ----------

    @mcp.tool()
    async def get_user_quotas(user_id: str | None = None) -> dict:
        """Get the resource quotas applied to a user.

        Args:
            user_id: User to inspect. Defaults to the API key's own user.

        Returns:
            RAM (MB), CPU cores, VM count and concurrent range limits
        """
        guard = await require_v2(client, "Quotas")
        if guard:
            return guard
        return await _call("Quotas", client.get_user_quotas(user_id))

    @mcp.tool()
    async def get_all_user_quotas() -> list | dict:
        """Get quotas for every user on the server (admin only).

        Use this to see who has room to deploy before assigning them a range.
        """
        guard = await require_v2(client, "Quotas")
        if guard:
            return guard
        return await _call("Quotas", client.get_all_user_quotas())

    @mcp.tool()
    async def get_default_quotas() -> dict:
        """Get the server-wide default quotas that new users inherit."""
        guard = await require_v2(client, "Quotas")
        if guard:
            return guard
        return await _call("Quotas", client.get_default_quotas())

    @mcp.tool()
    async def set_user_quotas(
        user_ids: list[str],
        quota_ram: int | None = None,
        quota_cpu: int | None = None,
        quota_vms: int | None = None,
        quota_ranges: int | None = None,
    ) -> dict:
        """Set resource quotas for one or more users (admin only).

        Only the quotas you pass are changed; omitted ones keep their current
        value. Setting a quota below what a user is already consuming does not
        tear anything down, but blocks their next deployment.

        Args:
            user_ids: Users to apply the quotas to, e.g. ["JD-jdoe"]
            quota_ram: RAM limit in MB (e.g. 32768 for 32 GB)
            quota_cpu: CPU core limit
            quota_vms: Maximum number of VMs
            quota_ranges: Maximum number of concurrent ranges
        """
        guard = await require_v2(client, "Quotas")
        if guard:
            return guard

        if not user_ids:
            return {"error": "user_ids must contain at least one user ID"}

        if all(v is None for v in (quota_ram, quota_cpu, quota_vms, quota_ranges)):
            return {
                "error": "No quota values supplied",
                "hint": "Pass at least one of quota_ram, quota_cpu, quota_vms, quota_ranges",
            }

        return await _call(
            "Quotas",
            client.set_user_quotas(
                user_ids, quota_ram, quota_cpu, quota_vms, quota_ranges
            ),
        )

    @mcp.tool()
    async def get_group_quotas() -> list | dict:
        """Get the default quotas configured for each group (admin only)."""
        guard = await require_v2(client, "Quotas")
        if guard:
            return guard
        return await _call("Quotas", client.get_group_quotas())

    @mcp.tool()
    async def set_group_quotas(
        group_names: list[str],
        default_quota_ram: int | None = None,
        default_quota_cpu: int | None = None,
        default_quota_vms: int | None = None,
        default_quota_ranges: int | None = None,
    ) -> dict:
        """Set default quotas for one or more groups (admin only).

        Group quotas apply to members who have no explicit per-user quota, which
        makes them the right tool for handing a class or team a uniform budget.

        Args:
            group_names: Groups to apply the defaults to
            default_quota_ram: RAM limit in MB
            default_quota_cpu: CPU core limit
            default_quota_vms: Maximum number of VMs
            default_quota_ranges: Maximum number of concurrent ranges
        """
        guard = await require_v2(client, "Quotas")
        if guard:
            return guard

        if not group_names:
            return {"error": "group_names must contain at least one group name"}

        if all(
            v is None
            for v in (
                default_quota_ram,
                default_quota_cpu,
                default_quota_vms,
                default_quota_ranges,
            )
        ):
            return {
                "error": "No quota values supplied",
                "hint": (
                    "Pass at least one of default_quota_ram, default_quota_cpu, "
                    "default_quota_vms, default_quota_ranges"
                ),
            }

        return await _call(
            "Quotas",
            client.set_group_quotas(
                group_names,
                default_quota_ram,
                default_quota_cpu,
                default_quota_vms,
                default_quota_ranges,
            ),
        )

    # ---------- Auto-shutdown ----------

    @mcp.tool()
    async def get_auto_shutdown(
        range_id: str | None = None, user_id: str | None = None
    ) -> dict:
        """Get the auto-shutdown timeout for a range.

        Args:
            range_id: Range to inspect. Defaults to the caller's range.
            user_id: Range owner, for admins inspecting someone else's range.
        """
        guard = await require_v2(client, "Auto-shutdown")
        if guard:
            return guard
        return await _call("Auto-shutdown", client.get_auto_shutdown(range_id, user_id))

    @mcp.tool()
    async def set_auto_shutdown(
        timeout_minutes: int,
        range_id: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Set how long a range may sit idle before it powers itself off.

        This is the main lever for keeping a shared Ludus host from filling up
        with forgotten running labs.

        Args:
            timeout_minutes: Idle minutes before shutdown. Pass 0 to disable.
            range_id: Range to configure. Defaults to the caller's range.
            user_id: Range owner, for admins configuring someone else's range.
        """
        guard = await require_v2(client, "Auto-shutdown")
        if guard:
            return guard

        if timeout_minutes < 0:
            return {
                "error": "timeout_minutes cannot be negative",
                "hint": "Use 0 to disable auto-shutdown",
            }

        result = await _call(
            "Auto-shutdown", client.set_auto_shutdown(timeout_minutes, range_id, user_id)
        )
        if isinstance(result, dict) and result.get("available") is False:
            return result
        return format_tool_response(
            {
                "autoShutdownTimeout": timeout_minutes,
                "enabled": timeout_minutes > 0,
                "result": result,
            }
        )

    # ---------- Deployment log history ----------

    @mcp.tool()
    async def list_range_log_history(
        range_id: str | None = None, user_id: str | None = None
    ) -> list | dict:
        """List previous range deployment logs, most recent first.

        get_range_logs only returns the log for the current or last deployment.
        This exposes the archive, which is what you want when comparing a
        failure against the deployment that last worked.

        Args:
            range_id: Range to list logs for. Defaults to the caller's range.
            user_id: Range owner, for admins.
        """
        guard = await require_v2(client, "Log history")
        if guard:
            return guard
        return format_tool_response(await client.list_range_log_history(range_id, user_id))

    @mcp.tool()
    async def get_range_log_from_history(
        log_id: str, range_id: str | None = None
    ) -> dict:
        """Get the full contents of one archived range deployment log.

        Args:
            log_id: Log ID from list_range_log_history
            range_id: Range the log belongs to. Defaults to the caller's range.
        """
        guard = await require_v2(client, "Log history")
        if guard:
            return guard
        return format_tool_response(
            await client.get_range_log_from_history(log_id, range_id)
        )

    @mcp.tool()
    async def list_template_log_history() -> list | dict:
        """List previous template build logs, most recent first.

        Use this to find why an earlier packer build failed once a newer build
        has already overwritten the live log.
        """
        guard = await require_v2(client, "Log history")
        if guard:
            return guard
        return format_tool_response(await client.list_template_log_history())

    @mcp.tool()
    async def get_template_log_from_history(log_id: str) -> dict:
        """Get the full contents of one archived template build log.

        Args:
            log_id: Log ID from list_template_log_history
        """
        guard = await require_v2(client, "Log history")
        if guard:
            return guard
        return format_tool_response(await client.get_template_log_from_history(log_id))

    return mcp

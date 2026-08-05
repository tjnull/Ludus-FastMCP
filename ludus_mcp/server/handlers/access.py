"""Access sharing and management handlers."""

from typing import Any
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class AccessHandler:
    """Handler for range access sharing and management."""

    def __init__(self, client: LudusAPIClient):
        """Initialize the access handler."""
        self.client = client

    async def get_range_access(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Get current access configuration for a range.

        Args:
            user_id: User ID (admin only)

        Returns:
            Access configuration
        """
        logger.info(f"Getting range access for user: {user_id or 'current'}")
        return await self.client.get_range_access(user_id)

    async def _resolve_range_id(
        self, range_id: str | None, user_id: str | None
    ) -> str:
        """Find the range these access changes apply to.

        v2 grants access per (user, range) pair, so every operation needs a
        concrete rangeID rather than an implicit "my range".
        """
        if range_id:
            return range_id

        range_info = await self.client.get_range(user_id)
        resolved = range_info.get("rangeID") or range_info.get("rangeNumber")
        if not resolved:
            raise ValueError(
                "Could not determine which range to change access for. "
                "Pass range_id explicitly."
            )
        return str(resolved)

    async def _current_users(self, range_id: str) -> list[str]:
        """List the user IDs that currently have access to a range."""
        entries = await self.client.list_range_users(range_id)
        users = []
        for entry in entries:
            if isinstance(entry, dict):
                uid = entry.get("userID") or entry.get("userId") or entry.get("id")
                if uid:
                    users.append(str(uid))
            elif isinstance(entry, str):
                users.append(entry)
        return users

    async def _apply(
        self,
        grant: list[str],
        revoke: list[str],
        range_id: str,
    ) -> dict[str, Any]:
        """Apply per-user grants and revokes, reporting each outcome."""
        granted, revoked, errors = [], [], []

        for user in grant:
            try:
                await self.client.assign_range_to_user(user, range_id)
                granted.append(user)
            except Exception as e:
                errors.append({"userID": user, "action": "grant", "error": str(e)})

        for user in revoke:
            try:
                await self.client.revoke_range_from_user(user, range_id)
                revoked.append(user)
            except Exception as e:
                errors.append({"userID": user, "action": "revoke", "error": str(e)})

        return {
            "rangeID": range_id,
            "granted": granted,
            "revoked": revoked,
            "errors": errors,
            "status": "error" if errors and not (granted or revoked) else "success",
            "allowedUsers": await self._current_users(range_id),
        }

    async def grant_range_access(
        self,
        users: list[str],
        user_id: str | None = None,
        range_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Grant other users access to a range.

        Args:
            users: List of user IDs to grant access to
            user_id: Range owner user ID (admin only)
            range_id: Range to share. Defaults to the owner's range.

        Returns:
            Which grants succeeded, plus the resulting user list
        """
        logger.info(f"Granting range access to users: {users}")

        if not users:
            return {"status": "error", "error": "No users supplied to grant access to"}

        resolved = await self._resolve_range_id(range_id, user_id)
        existing = await self._current_users(resolved)
        to_grant = [u for u in users if u not in existing]

        result = await self._apply(to_grant, [], resolved)
        result["already_had_access"] = [u for u in users if u in existing]
        return result

    async def revoke_range_access(
        self,
        users: list[str],
        user_id: str | None = None,
        range_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Revoke access to a range from specific users.

        Args:
            users: List of user IDs to revoke access from
            user_id: Range owner user ID (admin only)
            range_id: Range to change. Defaults to the owner's range.

        Returns:
            Which revocations succeeded, plus the resulting user list
        """
        logger.info(f"Revoking range access from users: {users}")

        if not users:
            return {"status": "error", "error": "No users supplied to revoke access from"}

        resolved = await self._resolve_range_id(range_id, user_id)
        existing = await self._current_users(resolved)
        to_revoke = [u for u in users if u in existing]

        result = await self._apply([], to_revoke, resolved)
        result["did_not_have_access"] = [u for u in users if u not in existing]
        return result

    async def set_range_access(
        self,
        users: list[str],
        user_id: str | None = None,
        range_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Set the complete list of users who can access a range.

        Users not in the list have their access revoked.

        Args:
            users: Complete list of user IDs who should have access
            user_id: Range owner user ID (admin only)
            range_id: Range to change. Defaults to the owner's range.

        Returns:
            Which grants and revocations were applied
        """
        logger.info(f"Setting range access to users: {users}")

        resolved = await self._resolve_range_id(range_id, user_id)
        existing = await self._current_users(resolved)

        return await self._apply(
            [u for u in users if u not in existing],
            [u for u in existing if u not in users],
            resolved,
        )

    async def clear_range_access(
        self, user_id: str | None = None, range_id: str | None = None
    ) -> dict[str, Any]:
        """
        Remove all access grants from a range.

        Args:
            user_id: Range owner user ID (admin only)
            range_id: Range to change. Defaults to the owner's range.

        Returns:
            Which revocations were applied
        """
        logger.info("Clearing all range access")

        resolved = await self._resolve_range_id(range_id, user_id)
        existing = await self._current_users(resolved)
        return await self._apply([], existing, resolved)

    def format_access_info(self, access: dict[str, Any], owner_id: str | None = None) -> str:
        """Format access information for display."""
        allowed_users = access.get("allowedUsers", [])

        lines = ["## Range Access Configuration\n"]

        if owner_id:
            lines.append(f"**Range Owner:** {owner_id}")
            lines.append("")

        if allowed_users:
            lines.append(f"**Shared with {len(allowed_users)} user(s):**")
            for user in allowed_users:
                lines.append(f"  • {user}")
            lines.append("")
            lines.append("### Actions:")
            lines.append("- Revoke access: `ludus.revoke_range_access(users=['user_id'])`")
            lines.append("- Clear all access: `ludus.clear_range_access()`")
        else:
            lines.append("**Access:** Private (no users granted access)")
            lines.append("")
            lines.append("### Actions:")
            lines.append("- Grant access: `ludus.grant_range_access(users=['user_id1', 'user_id2'])`")

        return "\n".join(lines)

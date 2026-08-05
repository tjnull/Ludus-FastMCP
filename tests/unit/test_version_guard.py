"""Tests for the server compatibility guard.

The guard no longer chooses between API shapes -- this release is v2-only. Its
job now is to turn an unusable server into one clear, actionable message at the
tool boundary instead of an exception from somewhere deeper.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ludus_mcp.exceptions import (
    LudusAPIError,
    LudusAuthenticationError,
    LudusConnectionError,
    LudusTimeoutError,
)
from ludus_mcp.utils.version_guard import require_v2


@pytest.mark.asyncio
async def test_guard_passes_when_the_server_verifies():
    client = MagicMock()
    client.ensure_server_verified = AsyncMock(return_value="2.3.0")

    assert await require_v2(client, "Blueprints") is None
    client.ensure_server_verified.assert_awaited_once()


@pytest.mark.asyncio
async def test_guard_reports_a_server_that_is_not_v2():
    client = MagicMock()
    client.ensure_server_verified = AsyncMock(
        side_effect=LudusAPIError(status_code=404, message="not v2")
    )

    result = await require_v2(client, "Blueprints")

    assert result is not None
    assert "Blueprints" in result["error"]
    assert "Ludus 2.0 or later" in result["error"]


@pytest.mark.asyncio
async def test_guard_reports_connection_failure_distinctly():
    """"Cannot reach the server" must not read as "your server is too old"."""
    client = MagicMock()
    client.ensure_server_verified = AsyncMock(
        side_effect=LudusConnectionError("refused")
    )

    result = await require_v2(client, "Groups")

    assert "cannot reach the Ludus server" in result["error"]


@pytest.mark.asyncio
async def test_guard_reports_timeout_as_unreachable():
    client = MagicMock()
    client.ensure_server_verified = AsyncMock(side_effect=LudusTimeoutError("slow"))

    result = await require_v2(client, "Groups")

    assert "cannot reach the Ludus server" in result["error"]


@pytest.mark.asyncio
async def test_guard_reports_bad_credentials_distinctly():
    client = MagicMock()
    client.ensure_server_verified = AsyncMock(
        side_effect=LudusAuthenticationError("bad key")
    )

    result = await require_v2(client, "Diagnostics")

    assert "authentication failed" in result["error"]


@pytest.mark.asyncio
async def test_guard_is_inert_without_a_verification_hook():
    """Handlers pass plain mocks in tests; the guard must not invent failures."""
    client = MagicMock(spec=[])

    assert await require_v2(client, "Groups") is None

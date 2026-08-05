"""Tests for compliance reporting when an individual control cannot be checked."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ludus_mcp.server.handlers.security_compliance import SecurityComplianceHandler


def _handler(list_snapshots_side_effect=None, snapshots=None):
    client = MagicMock()
    client.get_range = AsyncMock(return_value={"VMs": [{"memory": 4096}]})
    if list_snapshots_side_effect is not None:
        client.list_snapshots = AsyncMock(side_effect=list_snapshots_side_effect)
    else:
        client.list_snapshots = AsyncMock(return_value=snapshots)
    return SecurityComplianceHandler(client)


def _control(result, name):
    return next(
        (c for c in result["compliance_results"]["checks"] if c["control"] == name), None
    )


@pytest.mark.asyncio
async def test_snapshot_check_failure_is_reported_not_swallowed():
    handler = _handler(list_snapshots_side_effect=RuntimeError("API unavailable"))

    result = await handler.compliance_check()

    backup = _control(result, "BACKUP-001")
    assert backup is not None, "the control must still appear in the report"
    assert backup["status"] == "unknown"
    assert "API unavailable" in backup["error"]
    assert result["overall_compliant"] is False


@pytest.mark.asyncio
async def test_compliant_when_snapshots_exist():
    handler = _handler(snapshots=[{"name": "snap1"}])

    result = await handler.compliance_check()

    assert _control(result, "BACKUP-001")["status"] == "compliant"
    assert result["overall_compliant"] is True


@pytest.mark.asyncio
async def test_non_compliant_when_no_snapshots():
    handler = _handler(snapshots=[])

    result = await handler.compliance_check()

    assert _control(result, "BACKUP-001")["status"] == "non_compliant"
    assert result["overall_compliant"] is False

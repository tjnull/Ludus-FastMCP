"""Tests for the health_check tool's ludus CLI result handling.

`ludus version` exits 0 even when it cannot reach the server: it prints the
client version plus [ERROR] lines and omits the "Ludus Server ..." line. Health
must be decided on the parsed server version, not the exit code.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ludus_mcp.server.tools.core import create_core_tools


CONNECTED_OUTPUT = (
    "[INFO]  Ludus client 1.11.5+b9fe95c\n"
    "[INFO]  Ludus Server 1.11.4+b1da5c6 - community license\n"
)
UNREACHABLE_OUTPUT = (
    "[INFO]  Ludus client 1.11.5+b9fe95c\n"
    "[ERROR] Get \"https://198.51.100.1:8080/api/v1/version\": dial tcp: connection refused\n"
)


async def _run_health_check(stdout="", stderr="", returncode=0):
    mcp = create_core_tools(MagicMock())
    tool = await mcp.get_tool("health_check")

    completed = subprocess.CompletedProcess(
        args=["ludus", "version"], returncode=returncode, stdout=stdout, stderr=stderr
    )
    with patch("shutil.which", return_value="/usr/local/bin/ludus"), \
            patch("subprocess.run", return_value=completed):
        return await tool.fn()


@pytest.mark.asyncio
async def test_health_check_healthy_when_server_version_parsed():
    result = await _run_health_check(stdout=CONNECTED_OUTPUT)

    assert result["status"] == "healthy"
    assert result["ludus_api"]["reachable"] is True
    assert result["ludus_api"]["server_version"] == "1.11.4+b1da5c6"
    assert result["ludus_api"]["license"] == "community license"


@pytest.mark.asyncio
async def test_health_check_unhealthy_when_server_unreachable_despite_exit_zero():
    result = await _run_health_check(stdout=UNREACHABLE_OUTPUT, returncode=0)

    assert result["status"] == "unhealthy"
    assert result["ludus_api"]["reachable"] is False
    assert "connection refused" in result["error"]
    # The client version is still useful for troubleshooting
    assert result["ludus_api"]["client_version"] == "1.11.5+b9fe95c"


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_nonzero_exit():
    result = await _run_health_check(stderr="boom", returncode=1)

    assert result["status"] == "unhealthy"
    assert result["ludus_api"]["reachable"] is False
    assert result["error"]


@pytest.mark.asyncio
async def test_health_check_reports_error_when_output_is_empty():
    result = await _run_health_check(stdout="", stderr="", returncode=0)

    assert result["status"] == "unhealthy"
    assert result["error"]  # never an empty string

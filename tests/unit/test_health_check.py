"""Tests for the health_check tool's ludus CLI result handling.

Fixtures below are real output captured from ludus client 2.3.1. Failures omit
the "Ludus Server" line and report the reason on [ERROR] and/or [FATAL] lines,
so health is decided on the parsed server version rather than the exit code
alone (older clients were reported to exit 0 on failure).
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ludus_mcp.server.tools.core import create_core_tools


LICENSED_OUTPUT = (
    "[INFO]  Ludus client 2.3.1+f8d0295c\n"
    "[INFO]  Ludus Server 2.3.0+02a3ffc8 - License active, expires: 2027-03-12 "
    "03:48:04, licensed to tj null - Seat 1 - 2026-03-09T23:08:10.695Z\n"
)
COMMUNITY_OUTPUT = (
    "[INFO]  Ludus client 1.11.5+b9fe95c\n"
    "[INFO]  Ludus Server 1.11.4+b1da5c6 - community license\n"
)
UNREACHABLE_OUTPUT = (
    "[INFO]  Ludus client 2.3.1+f8d0295c\n"
    "[FATAL] Get \"https://192.0.2.99:8080/api/v2/\": dial tcp 192.0.2.99:8080: "
    "connect: no route to host\n"
)
BAD_KEY_OUTPUT = (
    "[INFO]  Ludus client 2.3.1+f8d0295c\n"
    "[ERROR] Error with request. Check your API key with --verbose\n"
    "[ERROR] User bogus from API key not found\n"
    "[FATAL] Request failed\n"
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
async def test_health_check_healthy_against_licensed_server():
    result = await _run_health_check(stdout=LICENSED_OUTPUT)

    assert result["status"] == "healthy"
    assert result["ludus_api"]["reachable"] is True
    assert result["ludus_api"]["server_version"] == "2.3.0+02a3ffc8"
    assert result["ludus_api"]["client_version"] == "2.3.1+f8d0295c"
    # The whole licence blurb is kept, including the " - " separated seat detail
    assert result["ludus_api"]["license"].startswith("License active, expires:")
    assert "Seat 1" in result["ludus_api"]["license"]


@pytest.mark.asyncio
async def test_health_check_healthy_against_community_server():
    result = await _run_health_check(stdout=COMMUNITY_OUTPUT)

    assert result["status"] == "healthy"
    assert result["ludus_api"]["server_version"] == "1.11.4+b1da5c6"
    assert result["ludus_api"]["license"] == "community license"


@pytest.mark.asyncio
async def test_health_check_unhealthy_when_server_unreachable():
    result = await _run_health_check(stdout=UNREACHABLE_OUTPUT, returncode=1)

    assert result["status"] == "unhealthy"
    assert result["ludus_api"]["reachable"] is False
    assert "no route to host" in result["error"]
    # The client version is still useful for troubleshooting
    assert result["ludus_api"]["client_version"] == "2.3.1+f8d0295c"


@pytest.mark.asyncio
async def test_health_check_unhealthy_on_bad_api_key():
    result = await _run_health_check(stdout=BAD_KEY_OUTPUT, returncode=1)

    assert result["status"] == "unhealthy"
    assert "API key" in result["error"]


@pytest.mark.asyncio
async def test_health_check_unhealthy_when_exit_zero_but_no_server_line():
    """Older clients were reported to exit 0 even when the request failed."""
    result = await _run_health_check(stdout=UNREACHABLE_OUTPUT, returncode=0)

    assert result["status"] == "unhealthy"
    assert result["ludus_api"]["reachable"] is False
    assert "no route to host" in result["error"]


@pytest.mark.asyncio
async def test_health_check_reports_error_when_output_is_empty():
    result = await _run_health_check(stdout="", stderr="", returncode=0)

    assert result["status"] == "unhealthy"
    assert result["error"]  # never an empty string

"""Tests for tool name listing (issue #6).

FastMCP 3.x's list_tools() returns one entry per tool version, so names can
repeat; --list-tools and the --verbose tool count both need unique names.
"""

import pytest

from ludus_mcp.server.main import _get_tool_names


class _Tool:
    def __init__(self, name):
        self.name = name


class FakeMCP:
    def __init__(self, *names):
        self._tools = [_Tool(name) for name in names]

    async def list_tools(self):
        return self._tools


@pytest.mark.asyncio
async def test_get_tool_names_returns_sorted_names():
    assert await _get_tool_names(FakeMCP("gamma", "alpha", "beta")) == [
        "alpha",
        "beta",
        "gamma",
    ]


@pytest.mark.asyncio
async def test_get_tool_names_deduplicates_repeated_versions():
    assert await _get_tool_names(FakeMCP("beta", "alpha", "beta")) == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_get_tool_names_handles_empty_server():
    assert await _get_tool_names(FakeMCP()) == []

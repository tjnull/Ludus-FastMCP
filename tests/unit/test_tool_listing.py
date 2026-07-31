"""Tests for FastMCP-version-agnostic tool name listing (issue #6)."""

import pytest

from ludus_mcp.server.main import _get_tool_names


class _Tool:
    def __init__(self, name):
        self.name = name


class FastMCP2Style:
    """FastMCP 2.x: get_tools() -> dict[str, Tool]."""

    async def get_tools(self):
        return {"beta": _Tool("beta"), "alpha": _Tool("alpha")}


class FastMCP3Style:
    """FastMCP 3.x: no get_tools(); list_tools() -> Sequence[Tool]."""

    async def list_tools(self):
        # 3.x returns one entry per tool version, so names can repeat
        return [_Tool("beta"), _Tool("alpha"), _Tool("beta")]


@pytest.mark.asyncio
async def test_get_tool_names_with_fastmcp_2_api():
    assert await _get_tool_names(FastMCP2Style()) == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_get_tool_names_with_fastmcp_3_api():
    assert await _get_tool_names(FastMCP3Style()) == ["alpha", "beta"]


@pytest.mark.asyncio
async def test_get_tool_names_returns_sorted_unique_names():
    names = await _get_tool_names(FastMCP3Style())
    assert names == sorted(set(names))

"""Tests for the v2-only tool guard."""

import pytest
from unittest.mock import MagicMock
from ludus_mcp.utils.version_guard import require_v2


def test_require_v2_returns_error_on_v1():
    client = MagicMock()
    client.api_version = "v1"
    result = require_v2(client, "Blueprints")
    assert result is not None
    assert "error" in result
    assert "Ludus 2.0" in result["error"]
    assert "Blueprints" in result["error"]


def test_require_v2_returns_none_on_v2():
    client = MagicMock()
    client.api_version = "v2"
    result = require_v2(client, "Blueprints")
    assert result is None


def test_require_v2_with_missing_attribute():
    client = MagicMock(spec=[])  # No api_version attribute
    result = require_v2(client, "Groups")
    assert result is not None
    assert "error" in result

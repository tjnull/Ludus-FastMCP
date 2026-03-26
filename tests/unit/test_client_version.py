"""Tests for API client version detection and path routing."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from ludus_mcp.core.client import LudusAPIClient


def _make_client(api_version="v1", api_key="test.apikey", jwt_token=""):
    """Helper to create client with specific settings."""
    with patch("ludus_mcp.core.client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ludus_api_url = "https://test.ludus.local:8080"
        settings.ludus_api_key = api_key
        settings.ludus_ssl_verify = False
        settings.ludus_api_version = api_version
        settings.ludus_jwt_token = jwt_token
        mock_settings.return_value = settings
        return LudusAPIClient()


def test_v1_client_has_empty_base_path():
    client = _make_client("v1")
    assert client.api_version == "v1"
    assert client._base_path == ""


def test_v2_client_has_api_v2_base_path():
    client = _make_client("v2")
    assert client.api_version == "v2"
    assert client._base_path == "/api/v2"


def test_auto_defaults_to_v1():
    client = _make_client("auto")
    assert client.api_version == "v1"
    assert hasattr(client, "_base_path")
    assert client._version_detected is False


@pytest.mark.asyncio
async def test_detect_version_finds_v2():
    client = _make_client("auto")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"version": "2.0.0"}
    client.client.request = AsyncMock(return_value=mock_response)
    await client.detect_version()
    assert client.api_version == "v2"
    assert client._base_path == "/api/v2"


@pytest.mark.asyncio
async def test_detect_version_falls_back_to_v1():
    client = _make_client("auto")
    mock_response_v1 = MagicMock()
    mock_response_v1.status_code = 200
    mock_response_v1.json.return_value = {"version": "1.5.0"}

    async def side_effect(**kwargs):
        if "/api/v2/" in kwargs.get("url", ""):
            raise httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
            )
        return mock_response_v1

    client.client.request = AsyncMock(side_effect=side_effect)
    await client.detect_version()
    assert client.api_version == "v1"
    assert client._base_path == ""


@pytest.mark.asyncio
async def test_detect_version_skipped_when_forced():
    client = _make_client("v2")
    client.client.request = AsyncMock()
    await client.detect_version()
    assert client.api_version == "v2"
    client.client.request.assert_not_called()


@pytest.mark.asyncio
async def test_request_prepends_base_path_v2():
    client = _make_client("v2")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"result": "ok"}'
    mock_response.json.return_value = {"result": "ok"}
    mock_response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=mock_response)
    client.rate_limiter = AsyncMock()
    client.rate_limiter.acquire = AsyncMock()
    await client._request("GET", "/range")
    call_kwargs = client.client.request.call_args
    assert call_kwargs.kwargs["url"] == "/api/v2/range"


@pytest.mark.asyncio
async def test_request_no_prefix_v1():
    client = _make_client("v1")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"result": "ok"}'
    mock_response.json.return_value = {"result": "ok"}
    mock_response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=mock_response)
    client.rate_limiter = AsyncMock()
    client.rate_limiter.acquire = AsyncMock()
    await client._request("GET", "/range")
    call_kwargs = client.client.request.call_args
    assert call_kwargs.kwargs["url"] == "/range"

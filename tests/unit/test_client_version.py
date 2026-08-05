"""Tests for server compatibility verification and path routing.

This release targets the Ludus 2.x API only. There is no version to detect and
no second API shape to route to -- what remains is confirming the server really
speaks v2, and failing with an actionable message when it does not.
"""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.exceptions import (
    LudusAPIError,
    LudusAuthenticationError,
    LudusConnectionError,
)


def _make_client(api_version="auto", api_key="test.apikey", jwt_token=""):
    """Helper to create a client with specific settings."""
    with patch("ludus_mcp.core.client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ludus_api_url = "https://test.ludus.local:8080"
        settings.ludus_api_key = api_key
        settings.ludus_ssl_verify = False
        settings.ludus_api_version = api_version
        settings.ludus_jwt_token = jwt_token
        settings.ludus_api_timeout = 120.0
        mock_settings.return_value = settings
        return LudusAPIClient()


def _response(status_code, payload=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload if payload is not None else {}
    return response


# ---------- routing ----------

def test_every_client_uses_the_v2_base_path():
    for setting in ("auto", "v2"):
        client = _make_client(setting)
        assert client.api_version == "v2"
        assert client._base_path == "/api/v2"


def test_v1_setting_is_rejected_with_guidance():
    """Silently ignoring LUDUS_API_VERSION=v1 would be worse than refusing."""
    with pytest.raises(ValueError) as excinfo:
        _make_client("v1")

    message = str(excinfo.value)
    assert "no longer supported" in message
    assert "2.0 or later" in message


@pytest.mark.asyncio
async def test_request_prepends_base_path():
    client = _make_client("v2")
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"result": "ok"}'
    response.json.return_value = {"result": "ok"}
    response.headers = {"content-type": "application/json"}
    response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=response)
    client.rate_limiter = AsyncMock()

    await client._request("GET", "/range")

    assert client.client.request.call_args.kwargs["url"] == "/api/v2/range"


# ---------- verification ----------

@pytest.mark.asyncio
async def test_verify_server_records_the_version():
    client = _make_client("auto")
    client.client.request = AsyncMock(
        return_value=_response(200, {"version": "2.3.0+02a3ffc8"})
    )

    version = await client.verify_server()

    assert version == "2.3.0+02a3ffc8"
    assert client.server_version == "2.3.0+02a3ffc8"
    assert client._server_verified is True


@pytest.mark.asyncio
async def test_verify_server_rejects_a_non_v2_server():
    """A v1 server 404s /api/v2/; say so instead of failing on every later call."""
    client = _make_client("auto")
    client.client.request = AsyncMock(return_value=_response(404))

    with pytest.raises(LudusAPIError) as excinfo:
        await client.verify_server()

    message = str(excinfo.value)
    assert "does not serve the Ludus 2.x API" in message
    assert "requires Ludus 2.0 or later" in message


@pytest.mark.asyncio
async def test_verify_server_distinguishes_bad_credentials():
    """401 means the key is wrong, not that the server is too old."""
    client = _make_client("auto")
    client.client.request = AsyncMock(return_value=_response(401))

    with pytest.raises(LudusAuthenticationError):
        await client.verify_server()


@pytest.mark.asyncio
async def test_verify_server_reports_connection_failure():
    client = _make_client("auto")
    client.client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(LudusConnectionError):
        await client.verify_server()


@pytest.mark.asyncio
async def test_verify_server_tolerates_a_missing_version_field():
    client = _make_client("auto")
    client.client.request = AsyncMock(return_value=_response(200, {"result": "ok"}))

    assert await client.verify_server() == "unknown"


@pytest.mark.asyncio
async def test_verification_happens_once_and_is_cached():
    client = _make_client("auto")

    async def mark_verified():
        client._server_verified = True
        client.server_version = "2.3.0"
        return "2.3.0"

    verify = AsyncMock(side_effect=mark_verified)
    with patch.object(client, "verify_server", verify):
        await client.ensure_server_verified()
        await client.ensure_server_verified()

    verify.assert_awaited_once()


@pytest.mark.asyncio
async def test_explicit_v2_setting_skips_the_verification_request():
    """Asserting the version should not cost a round-trip."""
    client = _make_client("v2")
    client.client.request = AsyncMock()

    await client.ensure_server_verified()

    client.client.request.assert_not_called()


@pytest.mark.asyncio
async def test_first_request_verifies_the_server():
    client = _make_client("auto")
    client.rate_limiter = AsyncMock()

    async def mark_verified():
        client._server_verified = True
        return "2.3.0"

    verify = AsyncMock(side_effect=mark_verified)
    response = MagicMock()
    response.status_code = 200
    response.content = b"{}"
    response.json.return_value = {}
    response.headers = {"content-type": "application/json"}
    response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=response)

    with patch.object(client, "verify_server", verify):
        await client._request("GET", "/range")

    verify.assert_awaited_once()

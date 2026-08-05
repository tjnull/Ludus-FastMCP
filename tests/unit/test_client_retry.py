"""Tests for API request retry behaviour.

_request used to carry an @async_retry decorator listing httpx exception types,
but the method converts those into Ludus* exceptions before they escape, so the
decorator never matched and nothing was ever retried.
"""

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.exceptions import LudusConnectionError, LudusTimeoutError


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LUDUS_API_KEY", "test-key")
    monkeypatch.setenv("LUDUS_API_URL", "https://ludus.example:8080")
    monkeypatch.setenv("LUDUS_API_VERSION", "v2")  # skip version detection
    import ludus_mcp.utils.config as config

    config._settings = None
    c = LudusAPIClient()
    yield c
    config._settings = None


@pytest.fixture(autouse=True)
def no_sleep():
    """Keep backoff from actually sleeping during tests."""
    with patch("ludus_mcp.core.client.asyncio.sleep", new=AsyncMock()):
        yield


@pytest.mark.asyncio
async def test_connection_error_is_retried_then_succeeds(client):
    attempts = 0

    async def flaky(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise LudusConnectionError("connection refused")
        return {"ok": True}

    with patch.object(client, "_send_request", side_effect=flaky):
        assert await client._request("GET", "/ranges") == {"ok": True}

    assert attempts == 3


@pytest.mark.asyncio
async def test_connection_error_gives_up_after_max_attempts(client):
    send = AsyncMock(side_effect=LudusConnectionError("down"))

    with patch.object(client, "_send_request", send):
        with pytest.raises(LudusConnectionError):
            await client._request("GET", "/ranges")

    assert send.await_count == client._RETRY_MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_timeout_is_retried_for_get(client):
    send = AsyncMock(side_effect=[LudusTimeoutError("slow"), {"ok": True}])

    with patch.object(client, "_send_request", send):
        assert await client._request("GET", "/ranges") == {"ok": True}

    assert send.await_count == 2


@pytest.mark.asyncio
async def test_timeout_is_not_replayed_for_post(client):
    """A timed-out POST may already have been executed server-side."""
    send = AsyncMock(side_effect=LudusTimeoutError("slow"))

    with patch.object(client, "_send_request", send):
        with pytest.raises(LudusTimeoutError):
            await client._request("POST", "/range/deploy", {"force": True})

    assert send.await_count == 1


@pytest.mark.asyncio
async def test_connection_error_is_retried_even_for_post(client):
    """A refused connection never reached the server, so replay is safe."""
    send = AsyncMock(side_effect=[LudusConnectionError("refused"), {"ok": True}])

    with patch.object(client, "_send_request", send):
        assert await client._request("POST", "/range/deploy") == {"ok": True}

    assert send.await_count == 2


@pytest.mark.asyncio
async def test_http_errors_are_not_retried(client):
    """4xx/5xx must surface immediately rather than being replayed."""
    from ludus_mcp.exceptions import LudusNotFoundError

    send = AsyncMock(side_effect=LudusNotFoundError("Resource not found: /nope"))

    with patch.object(client, "_send_request", send):
        with pytest.raises(LudusNotFoundError):
            await client._request("GET", "/nope")

    assert send.await_count == 1


@pytest.mark.asyncio
async def test_httpx_timeout_is_converted_and_retried_end_to_end(client):
    """The real conversion path: httpx error -> Ludus error -> retry loop."""
    calls = 0

    async def transport(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("no route to host")
        response = httpx.Response(200, json={"ok": True})
        response.request = httpx.Request("GET", "https://ludus.example:8080/ranges")
        return response

    with patch.object(client.client, "request", side_effect=transport):
        assert await client._request("GET", "/ranges") == {"ok": True}

    assert calls == 2

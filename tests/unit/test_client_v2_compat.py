"""Tests for v1/v2 endpoint compatibility."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ludus_mcp.core.client import LudusAPIClient


def _make_client(api_version):
    with patch("ludus_mcp.core.client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ludus_api_url = "https://test.ludus.local:8080"
        settings.ludus_api_key = "test.apikey"
        settings.ludus_ssl_verify = False
        settings.ludus_api_version = api_version
        settings.ludus_jwt_token = ""
        mock_settings.return_value = settings
        client = LudusAPIClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"result": "ok"}'
    mock_response.json.return_value = {"result": "ok"}
    mock_response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=mock_response)
    client.rate_limiter = AsyncMock()
    client.rate_limiter.acquire = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_build_template_v1_uses_template_string():
    client = _make_client("v1")
    await client.build_template(template_name="kali-linux")
    call_kwargs = client.client.request.call_args.kwargs
    assert "template_name" in call_kwargs.get("json", {})


@pytest.mark.asyncio
async def test_build_template_v2_uses_templates_array():
    client = _make_client("v2")
    await client.build_template(template_name="kali-linux")
    call_kwargs = client.client.request.call_args.kwargs
    assert "templates" in call_kwargs.get("json", {})
    assert isinstance(call_kwargs["json"]["templates"], list)


@pytest.mark.asyncio
async def test_add_user_v1_no_email():
    client = _make_client("v1")
    await client.add_user(user_id="testuser", name="Test User")
    call_kwargs = client.client.request.call_args.kwargs
    assert "email" not in call_kwargs.get("json", {})


@pytest.mark.asyncio
async def test_add_user_v2_includes_email():
    client = _make_client("v2")
    await client.add_user(user_id="testuser", name="Test User", email="test@example.com")
    call_kwargs = client.client.request.call_args.kwargs
    assert call_kwargs["json"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_reset_password_v1_uses_passwordreset():
    client = _make_client("v1")
    await client.reset_user_proxmox_password("testuser")
    call_kwargs = client.client.request.call_args.kwargs
    assert call_kwargs["url"] == "/user/passwordreset"


@pytest.mark.asyncio
async def test_reset_password_v2_uses_credentials():
    client = _make_client("v2")
    await client.reset_user_proxmox_password("testuser")
    call_kwargs = client.client.request.call_args.kwargs
    assert call_kwargs["url"] == "/api/v2/user/credentials"


@pytest.mark.asyncio
async def test_get_range_access_v1():
    client = _make_client("v1")
    await client.get_range_access()
    assert client.client.request.call_args.kwargs["url"] == "/range/access"


@pytest.mark.asyncio
async def test_get_range_access_v2():
    client = _make_client("v2")
    await client.get_range_access()
    assert client.client.request.call_args.kwargs["url"] == "/api/v2/ranges/accessible"

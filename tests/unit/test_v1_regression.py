"""Regression tests ensuring all existing tools work identically on v1."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ludus_mcp.core.client import LudusAPIClient


@pytest.fixture
def v1_client():
    with patch("ludus_mcp.core.client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ludus_api_url = "https://test.ludus.local:8080"
        settings.ludus_api_key = "test.apikey"
        settings.ludus_ssl_verify = False
        settings.ludus_api_version = "v1"
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
async def test_v1_get_range(v1_client):
    await v1_client.get_range()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range"


@pytest.mark.asyncio
async def test_v1_list_ranges(v1_client):
    await v1_client.list_ranges()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/all"


@pytest.mark.asyncio
async def test_v1_deploy_range(v1_client):
    await v1_client.deploy_range()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/deploy"


@pytest.mark.asyncio
async def test_v1_get_range_config(v1_client):
    v1_client.client.request.return_value.json.return_value = {"result": "key: value"}
    await v1_client.get_range_config()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/config"


@pytest.mark.asyncio
async def test_v1_power_on(v1_client):
    await v1_client.power_on_range()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/poweron"


@pytest.mark.asyncio
async def test_v1_power_off(v1_client):
    await v1_client.power_off_range()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/poweroff"


@pytest.mark.asyncio
async def test_v1_list_snapshots(v1_client):
    v1_client.client.request.return_value.json.return_value = []
    await v1_client.list_snapshots()
    assert v1_client.client.request.call_args.kwargs["url"] == "/snapshots/list"


@pytest.mark.asyncio
async def test_v1_list_templates(v1_client):
    v1_client.client.request.return_value.json.return_value = []
    await v1_client.list_templates()
    assert v1_client.client.request.call_args.kwargs["url"] == "/templates"


@pytest.mark.asyncio
async def test_v1_list_users(v1_client):
    v1_client.client.request.return_value.json.return_value = []
    await v1_client.list_users()
    assert v1_client.client.request.call_args.kwargs["url"] == "/user/all"


@pytest.mark.asyncio
async def test_v1_get_user(v1_client):
    await v1_client.get_user()
    assert v1_client.client.request.call_args.kwargs["url"] == "/user"


@pytest.mark.asyncio
async def test_v1_get_range_access(v1_client):
    await v1_client.get_range_access()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/access"


@pytest.mark.asyncio
async def test_v1_start_testing(v1_client):
    await v1_client.start_testing()
    assert v1_client.client.request.call_args.kwargs["url"] == "/testing/start"


@pytest.mark.asyncio
async def test_v1_stop_testing(v1_client):
    await v1_client.stop_testing()
    assert v1_client.client.request.call_args.kwargs["url"] == "/testing/stop"


@pytest.mark.asyncio
async def test_v1_list_ansible_resources(v1_client):
    await v1_client.list_ansible_resources()
    assert v1_client.client.request.call_args.kwargs["url"] == "/ansible"


@pytest.mark.asyncio
async def test_v1_reset_password(v1_client):
    await v1_client.reset_user_proxmox_password("testuser")
    assert v1_client.client.request.call_args.kwargs["url"] == "/user/passwordreset"


@pytest.mark.asyncio
async def test_v1_get_range_logs(v1_client):
    await v1_client.get_range_logs()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/logs"


@pytest.mark.asyncio
async def test_v1_get_range_etchosts(v1_client):
    await v1_client.get_range_etchosts()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/etchosts"


@pytest.mark.asyncio
async def test_v1_get_range_sshconfig(v1_client):
    await v1_client.get_range_sshconfig()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/sshconfig"


@pytest.mark.asyncio
async def test_v1_get_range_rdpconfigs(v1_client):
    await v1_client.get_range_rdpconfigs()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/rdpconfigs"


@pytest.mark.asyncio
async def test_v1_get_ansible_inventory(v1_client):
    await v1_client.get_range_ansible_inventory()
    assert v1_client.client.request.call_args.kwargs["url"] == "/range/ansibleinventory"


@pytest.mark.asyncio
async def test_v1_get_user_wireguard(v1_client):
    v1_client.client.request.return_value.json.return_value = {"result": {"wireGuardConfig": ""}}
    await v1_client.get_user_wireguard()
    assert v1_client.client.request.call_args.kwargs["url"] == "/user/wireguard"


@pytest.mark.asyncio
async def test_v1_get_user_apikey(v1_client):
    await v1_client.get_user_apikey()
    assert v1_client.client.request.call_args.kwargs["url"] == "/user/apikey"


@pytest.mark.asyncio
async def test_v1_no_base_path_prefix(v1_client):
    """Verify NO endpoint gets /api/v2 prefix on v1."""
    endpoints_to_test = [
        ("get_range", {}),
        ("list_templates", {}),
        ("list_snapshots", {}),
        ("power_on_range", {}),
        ("start_testing", {}),
    ]
    for method_name, kwargs in endpoints_to_test:
        v1_client.client.request.reset_mock()
        v1_client.client.request.return_value.json.return_value = []
        v1_client.client.request.return_value.content = b'[]'
        v1_client.client.request.return_value.raise_for_status = MagicMock()
        method = getattr(v1_client, method_name)
        await method(**kwargs)
        url = v1_client.client.request.call_args.kwargs["url"]
        assert not url.startswith("/api/v2"), f"{method_name} should not use /api/v2 prefix on v1, got {url}"

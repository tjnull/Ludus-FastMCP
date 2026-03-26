"""Tests for new v2 API client methods."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ludus_mcp.core.client import LudusAPIClient


@pytest.fixture
def v2_client():
    with patch("ludus_mcp.core.client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ludus_api_url = "https://test.ludus.local:8080"
        settings.ludus_api_key = "test.apikey"
        settings.ludus_ssl_verify = False
        settings.ludus_api_version = "v2"
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
async def test_list_groups(v2_client):
    await v2_client.list_groups()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/groups"

@pytest.mark.asyncio
async def test_create_group(v2_client):
    await v2_client.create_group(name="red-team")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/groups"
    assert v2_client.client.request.call_args.kwargs["method"] == "POST"

@pytest.mark.asyncio
async def test_delete_group(v2_client):
    await v2_client.delete_group(group_name="red-team")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/groups/red-team"

@pytest.mark.asyncio
async def test_add_users_to_group(v2_client):
    await v2_client.add_users_to_group(group_name="red-team", user_ids=["u1"])
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/groups/red-team/users"

@pytest.mark.asyncio
async def test_destroy_vm(v2_client):
    await v2_client.destroy_vm(vm_id="vm-123")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/vm/vm-123"
    assert v2_client.client.request.call_args.kwargs["method"] == "DELETE"

@pytest.mark.asyncio
async def test_get_console_ticket(v2_client):
    await v2_client.get_console_ticket(vm_id="vm-123")
    assert "/api/v2/vm/console/ticket" in v2_client.client.request.call_args.kwargs["url"]

@pytest.mark.asyncio
async def test_get_diagnostics(v2_client):
    await v2_client.get_diagnostics()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/diagnostics"

@pytest.mark.asyncio
async def test_get_sdn_migration_status(v2_client):
    await v2_client.get_sdn_migration_status()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/migrate/sdn/status"

@pytest.mark.asyncio
async def test_create_range(v2_client):
    await v2_client.create_range(name="test-range")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/ranges/create"

@pytest.mark.asyncio
async def test_assign_range_to_user(v2_client):
    await v2_client.assign_range_to_user(user_id="u1", range_id="r1")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/ranges/assign/u1/r1"

@pytest.mark.asyncio
async def test_list_accessible_ranges(v2_client):
    await v2_client.list_accessible_ranges()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/ranges/accessible"

@pytest.mark.asyncio
async def test_get_default_range(v2_client):
    await v2_client.get_default_range()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/user/default-range"

@pytest.mark.asyncio
async def test_whoami(v2_client):
    await v2_client.whoami()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/whoami"

@pytest.mark.asyncio
async def test_move_role_scope(v2_client):
    await v2_client.move_role_scope(role_name="test-role", scope="global")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/ansible/role/scope"

@pytest.mark.asyncio
async def test_provision_oauth2_user(v2_client):
    await v2_client.provision_oauth2_user(config={"email": "test@example.com"})
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/user/provision-oauth2"

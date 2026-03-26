"""Tests for blueprint API client methods."""
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
    mock_response.content = b'[{"id": "bp-1"}]'
    mock_response.json.return_value = [{"id": "bp-1"}]
    mock_response.raise_for_status = MagicMock()
    client.client.request = AsyncMock(return_value=mock_response)
    client.rate_limiter = AsyncMock()
    client.rate_limiter.acquire = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_list_blueprints(v2_client):
    await v2_client.list_blueprints()
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/blueprints"

@pytest.mark.asyncio
async def test_create_blueprint_from_range(v2_client):
    await v2_client.create_blueprint_from_range(range_id="range-1")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/blueprints/from-range"

@pytest.mark.asyncio
async def test_apply_blueprint(v2_client):
    await v2_client.apply_blueprint(blueprint_id="bp-1", range_id="range-1")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/blueprints/bp-1/apply"

@pytest.mark.asyncio
async def test_delete_blueprint(v2_client):
    await v2_client.delete_blueprint(blueprint_id="bp-1")
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/blueprints/bp-1"
    assert v2_client.client.request.call_args.kwargs["method"] == "DELETE"

@pytest.mark.asyncio
async def test_share_blueprint_with_users(v2_client):
    await v2_client.share_blueprint_with_users(blueprint_id="bp-1", user_ids=["user1"])
    assert v2_client.client.request.call_args.kwargs["url"] == "/api/v2/blueprints/bp-1/share/users"

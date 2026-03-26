"""Tests for authentication header behavior."""

import pytest
from unittest.mock import patch, MagicMock
from ludus_mcp.core.client import LudusAPIClient


def _make_client(api_key="test.apikey", jwt_token="", api_version="v1"):
    with patch("ludus_mcp.core.client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.ludus_api_url = "https://test.ludus.local:8080"
        settings.ludus_api_key = api_key
        settings.ludus_ssl_verify = False
        settings.ludus_api_version = api_version
        settings.ludus_jwt_token = jwt_token
        mock_settings.return_value = settings
        return LudusAPIClient()


def test_api_key_only():
    client = _make_client(api_key="test.apikey", jwt_token="")
    assert client.client.headers.get("x-api-key") == "test.apikey" or client.client.headers.get("X-API-KEY") == "test.apikey"
    assert "authorization" not in [k.lower() for k in client.client.headers.keys()]


def test_jwt_only():
    client = _make_client(api_key="", jwt_token="my.jwt.token")
    auth = client.client.headers.get("authorization") or client.client.headers.get("Authorization")
    assert auth == "Bearer my.jwt.token"
    assert "x-api-key" not in [k.lower() for k in client.client.headers.keys()]


def test_both_jwt_and_apikey_prefers_jwt():
    client = _make_client(api_key="test.apikey", jwt_token="my.jwt.token")
    auth = client.client.headers.get("authorization") or client.client.headers.get("Authorization")
    assert auth == "Bearer my.jwt.token"
    assert "x-api-key" not in [k.lower() for k in client.client.headers.keys()]

"""Tests for configuration settings."""

import os
import pytest
from unittest.mock import patch


def test_default_api_version():
    """Default LUDUS_API_VERSION should be 'auto'."""
    with patch.dict(os.environ, {}, clear=True):
        from ludus_mcp.utils.config import Settings
        settings = Settings(ludus_api_url="http://localhost:8080", ludus_api_key="test")
        assert settings.ludus_api_version == "auto"


def test_default_jwt_token():
    """Default LUDUS_JWT_TOKEN should be empty string."""
    with patch.dict(os.environ, {}, clear=True):
        from ludus_mcp.utils.config import Settings
        settings = Settings(ludus_api_url="http://localhost:8080", ludus_api_key="test")
        assert settings.ludus_jwt_token == ""


def test_api_version_from_env():
    """LUDUS_API_VERSION should be read from environment."""
    with patch.dict(os.environ, {"LUDUS_API_VERSION": "v2"}, clear=False):
        from ludus_mcp.utils.config import Settings
        settings = Settings(ludus_api_url="http://localhost:8080", ludus_api_key="test")
        assert settings.ludus_api_version == "v2"


def test_jwt_token_from_env():
    """LUDUS_JWT_TOKEN should be read from environment."""
    with patch.dict(os.environ, {"LUDUS_JWT_TOKEN": "my.jwt.token"}, clear=False):
        from ludus_mcp.utils.config import Settings
        settings = Settings(ludus_api_url="http://localhost:8080", ludus_api_key="test")
        assert settings.ludus_jwt_token == "my.jwt.token"

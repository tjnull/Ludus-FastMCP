"""Tests for the v2 content-sources support and template building."""

import pytest
from unittest.mock import AsyncMock, patch

from ludus_mcp.core.client import LudusAPIClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LUDUS_API_KEY", "test-key")
    monkeypatch.setenv("LUDUS_API_URL", "https://ludus.example:8080")
    monkeypatch.setenv("LUDUS_API_VERSION", "v2")
    import ludus_mcp.utils.config as config

    config._settings = None
    c = LudusAPIClient()
    yield c
    config._settings = None


@pytest.mark.asyncio
async def test_install_from_source_builds_selection_payload(client):
    send = AsyncMock(return_value={"ok": True})
    with patch.object(client, "_send_request", send):
        await client.install_from_source(
            "ludus-source-bsl",
            templates=["remnux-template"],
            blueprints=["goad"],
            roles=["some.role"],
            collections=["ns.coll"],
        )

    method, endpoint, payload = send.await_args.args[:3]
    assert method == "POST"
    assert endpoint == "/sources/ludus-source-bsl/install"
    assert payload["selection"] == {
        "templates": ["remnux-template"],
        "blueprints": ["goad"],
        "localRoles": ["some.role"],
        "localCollections": ["ns.coll"],
    }
    # optional flags stay out of the payload unless asked for
    assert "global" not in payload and "force" not in payload and "noDeps" not in payload


@pytest.mark.asyncio
async def test_install_from_source_requires_a_selection(client):
    with patch.object(client, "_send_request", AsyncMock()):
        with pytest.raises(ValueError, match="at least one of"):
            await client.install_from_source("ludus-source-bsl")


@pytest.mark.asyncio
async def test_install_from_source_flags(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.install_from_source(
            "src", templates=["t"], install_globally=True, force=True, no_deps=True
        )
    payload = send.await_args.args[2]
    assert payload["global"] is True and payload["force"] is True and payload["noDeps"] is True


@pytest.mark.asyncio
async def test_list_sources_tolerates_non_list_payload(client):
    with patch.object(client, "_send_request", AsyncMock(return_value={"unexpected": True})):
        assert await client.list_sources() == []


@pytest.mark.asyncio
async def test_build_template_uses_v2_endpoint_and_accepts_a_list(client):
    """v2 builds via POST /templates; /templates/build is the v1 path."""
    send = AsyncMock(return_value={"result": "started"})
    with patch.object(client, "_send_request", send):
        await client.build_template(["debian-12-x64-server-template", "kali-x64-desktop-template"],
                                    parallel=2)

    method, endpoint, payload = send.await_args.args[:3]
    assert (method, endpoint) == ("POST", "/templates")
    assert payload["templates"] == ["debian-12-x64-server-template", "kali-x64-desktop-template"]
    assert payload["parallel"] == 2


@pytest.mark.asyncio
async def test_build_template_accepts_a_single_name(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.build_template("remnux-template")
    assert send.await_args.args[2]["templates"] == ["remnux-template"]



@pytest.mark.asyncio
async def test_build_all_templates_sends_no_names(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.build_template()
    payload = send.await_args.args[2]
    assert "templates" not in payload and payload["parallel"] == 1

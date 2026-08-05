"""Regressions for bugs found while validating against a live Ludus 2.3.0 server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.validation import ValidationHandler


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LUDUS_API_KEY", "test-key")
    monkeypatch.setenv("LUDUS_API_URL", "https://ludus.example:8080")
    monkeypatch.delenv("LUDUS_API_VERSION", raising=False)
    import ludus_mcp.utils.config as config

    config._settings = None
    c = LudusAPIClient()
    yield c
    config._settings = None


@pytest.mark.asyncio
async def test_add_user_sends_email(client):
    """The API rejects user creation without an email ("Email is required")."""
    client._server_verified = True
    with patch.object(client, "_send_request", AsyncMock(return_value={"ok": True})) as send:
        await client.add_user("BOB", "Bob", email="bob@ludus.internal")

    assert send.await_args.args[2]["email"] == "bob@ludus.internal"


@pytest.mark.asyncio
async def test_add_user_without_email_fails_clearly(client):
    client._server_verified = True
    with patch.object(client, "_send_request", AsyncMock()):
        with pytest.raises(ValueError, match="requires an email"):
            await client.add_user("BOB", "Bob")


@pytest.mark.asyncio
async def test_get_user_unwraps_single_element_list(client):
    """GET /user answers with a list even for one user; the tool declares dict."""
    client._server_verified = True
    with patch.object(client, "_send_request",
                      AsyncMock(return_value=[{"userID": "BOB", "name": "Bob"}])):
        result = await client.get_user("BOB")
    assert isinstance(result, dict)
    assert result["userID"] == "BOB"


@pytest.mark.asyncio
async def test_get_user_handles_empty_list(client):
    client._server_verified = True
    with patch.object(client, "_send_request", AsyncMock(return_value=[])):
        assert await client.get_user("NOBODY") == {}


def test_timeout_is_configurable(monkeypatch):
    monkeypatch.setenv("LUDUS_API_KEY", "k")
    monkeypatch.setenv("LUDUS_API_TIMEOUT", "45")
    import ludus_mcp.utils.config as config

    config._settings = None
    try:
        assert LudusAPIClient().timeout == 45.0
    finally:
        config._settings = None


@pytest.mark.asyncio
async def test_validate_config_accepts_real_ludus_list_format():
    """Real configs put a LIST under "ludus"; treating it as a dict crashed."""
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[{"name": "debian-12-x64-server-template"}])
    handler = ValidationHandler(client)

    config = {
        "ludus": [
            {
                "vm_name": "{{ range_id }}-deb12",
                "hostname": "{{ range_id }}-DEB12",
                "template": "debian-12-x64-server-template",
                "vlan": 10,
                "ip_last_octet": 5,
                "ram_gb": 2,
                "cpus": 2,
            }
        ]
    }

    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    assert data["valid"] is True
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_validate_config_still_accepts_dict_format():
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[{"name": "debian-12-x64-server-template"}])
    handler = ValidationHandler(client)

    config = {
        "ludus": {
            "vms": [
                {
                    "vm_name": "vm1",
                    "hostname": "vm1",
                    "template": "debian-12-x64-server-template",
                    "vlan": 10,
                    "ip_last_octet": 5,
                    "ram_gb": 2,
                    "cpus": 2,
                }
            ]
        }
    }

    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_validate_config_rejects_unknown_template():
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[{"name": "debian-12-x64-server-template"}])
    handler = ValidationHandler(client)

    config = {"ludus": [{"vm_name": "x", "hostname": "x", "template": "nope",
                         "vlan": 10, "ip_last_octet": 5, "ram_gb": 2, "cpus": 2}]}

    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    assert data["valid"] is False
    assert any("nope" in (e.message if hasattr(e, "message") else str(e)) for e in data["errors"])


@pytest.mark.asyncio
async def test_update_range_config_uses_the_v2_base_path(client):
    """The config upload bypasses _request(), so it builds its own URL.

    It once posted to /range/config instead of /api/v2/range/config and 404'd on
    every Ludus 2.x server.
    """
    client._server_verified = True
    captured = {}

    async def fake_request(**kwargs):
        captured.update(kwargs)

        class R:
            status_code = 200
            content = b"{}"

            def raise_for_status(self):
                return None

            def json(self):
                return {}

        return R()

    with patch.object(client.client, "request", side_effect=fake_request):
        await client.update_range_config({"ludus": [{"vm_name": "a"}]})

    assert captured["url"] == "/api/v2/range/config", "config upload must use the v2 base path"


def test_no_client_method_branches_on_the_api_version():
    """v1 support is gone; version branching must not creep back in.

    Every endpoint lives under /api/v2. A method that starts choosing shapes
    again is reintroducing the dual-API complexity this release removed.
    """
    import ast
    import pathlib

    source = pathlib.Path("ludus_mcp/core/client.py").read_text()
    tree = ast.parse(source)
    exempt = {"__init__", "verify_server"}

    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        if node.name in exempt:
            continue
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Compare)
                and isinstance(sub.left, ast.Attribute)
                and sub.left.attr in ("api_version", "_version_setting")
            ):
                offenders.append(f"{node.name}() at line {sub.lineno}")

    assert not offenders, (
        "These client methods branch on the API version, but this release is "
        "Ludus 2.x only:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.asyncio
async def test_list_snapshots_unwraps_the_snapshots_key(client):
    """The API answers {"snapshots": [...]}; treating a dict as empty hid them all."""
    client._server_verified = True
    payload = {"snapshots": [{"name": "snap1", "vmid": 107, "vmname": "vm"}]}
    with patch.object(client, "_send_request", AsyncMock(return_value=payload)):
        result = await client.list_snapshots()
    assert result == payload["snapshots"]


@pytest.mark.asyncio
async def test_list_snapshots_handles_a_bare_list_and_junk(client):
    client._server_verified = True
    with patch.object(client, "_send_request", AsyncMock(return_value=[{"name": "s"}])):
        assert await client.list_snapshots() == [{"name": "s"}]
    with patch.object(client, "_send_request", AsyncMock(return_value={"unexpected": 1})):
        assert await client.list_snapshots() == []


@pytest.mark.asyncio
async def test_resolve_vm_ids_maps_names_to_proxmox_ids(client):
    """Snapshot endpoints select by vmid; a name they don't understand hits every VM."""
    range_info = {"VMs": [
        {"name": "r-router", "proxmoxID": 106},
        {"name": "r-deb12", "proxmoxID": 107},
    ]}
    with patch.object(client, "get_range", AsyncMock(return_value=range_info)):
        assert await client.resolve_vm_ids("r-deb12") == [107]
        assert await client.resolve_vm_ids(["r-router", "r-deb12"]) == [106, 107]
        # None means "whole range" - the API treats an empty vmids list that way
        assert await client.resolve_vm_ids(None) == []


@pytest.mark.asyncio
async def test_resolve_vm_ids_rejects_unknown_names(client):
    """Better a loud error than silently snapshotting/rolling back every VM."""
    range_info = {"VMs": [{"name": "r-deb12", "proxmoxID": 107}]}
    with patch.object(client, "get_range", AsyncMock(return_value=range_info)):
        with pytest.raises(ValueError, match="not found in range: ghost"):
            await client.resolve_vm_ids(["ghost"])


@pytest.mark.asyncio
async def test_validate_config_accepts_inter_vlan_rules():
    """network.rules are FIREWALL rules, not networks - they never have a CIDR.

    Validating them as networks rejected every real config with inter-VLAN
    rules, e.g. the AD + Elastic blueprint.
    """
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[{"name": "debian-12-x64-server-template"}])
    handler = ValidationHandler(client)

    config = {
        "ludus": [{"vm_name": "vm1", "hostname": "vm1",
                   "template": "debian-12-x64-server-template",
                   "vlan": 10, "ip_last_octet": 5, "ram_gb": 2, "cpus": 2}],
        "network": {
            "inter_vlan_default": "ACCEPT",
            "rules": [
                {"name": "Allow Kali to AD", "vlan_src": 99, "vlan_dst": 10,
                 "protocol": "all", "ports": "all", "action": "ACCEPT"},
            ],
        },
    }

    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    assert data["valid"] is True, [getattr(e, "message", e) for e in data["errors"]]


@pytest.mark.asyncio
async def test_validate_config_still_catches_broken_vlan_rules():
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[{"name": "debian-12-x64-server-template"}])
    handler = ValidationHandler(client)

    config = {
        "ludus": [{"vm_name": "vm1", "hostname": "vm1",
                   "template": "debian-12-x64-server-template",
                   "vlan": 10, "ip_last_octet": 5, "ram_gb": 2, "cpus": 2}],
        "network": {"rules": [{"name": "broken", "vlan_dst": 20, "action": "MAYBE"}]},
    }

    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    messages = " ".join(getattr(e, "message", str(e)) for e in data["errors"])
    assert data["valid"] is False
    assert "missing vlan_src" in messages
    assert "invalid action" in messages

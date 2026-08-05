"""Tests for API payload shapes the client previously mishandled.

Each of these produced a live failure: a null status broke MCP output
validation, the role-vars field name was rejected by the API, and the network
block was read from the wrong place in the config.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.network_analysis import NetworkAnalysisHandler


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LUDUS_API_KEY", "k")
    monkeypatch.setenv("LUDUS_API_URL", "https://ludus.example:8080")
    monkeypatch.setenv("LUDUS_API_VERSION", "v2")
    import ludus_mcp.utils.config as config
    config._settings = None
    c = LudusAPIClient()
    yield c
    config._settings = None


@pytest.mark.asyncio
async def test_template_status_null_becomes_structured(client):
    """The API returns `null` when idle; None fails MCP output validation."""
    with patch.object(client, "_send_request", AsyncMock(return_value=None)):
        assert await client.get_template_status() == {"building": [], "status": "idle"}


@pytest.mark.asyncio
async def test_template_status_list_is_wrapped(client):
    payload = [{"user": "tjnull", "template": "win2022-server-x64-template"}]
    with patch.object(client, "_send_request", AsyncMock(return_value=payload)):
        result = await client.get_template_status()
    assert result["status"] == "building"
    assert result["building"] == payload


@pytest.mark.asyncio
async def test_get_role_vars_sends_roles_array(client):
    """The API field is "roles"; {"name": ...} was rejected."""
    send = AsyncMock(return_value={"roles": []})
    with patch.object(client, "_send_request", send):
        await client.get_role_vars("some.role")
    assert send.await_args.args[2] == {"roles": ["some.role"]}


@pytest.mark.asyncio
async def test_get_role_vars_accepts_a_list(client):
    send = AsyncMock(return_value={"roles": []})
    with patch.object(client, "_send_request", send):
        await client.get_role_vars(["a.b", "c.d"])
    assert send.await_args.args[2] == {"roles": ["a.b", "c.d"]}


@pytest.mark.asyncio
async def test_network_topology_reads_the_real_config_shape():
    """config["ludus"] is a LIST of VMs; the network block is top level."""
    client = MagicMock()
    client.get_range = AsyncMock(return_value={"VMs": [
        {"name": "r-dc", "ip": "10.1.10.10"},
        {"name": "r-kali", "ip": "10.1.99.10"},
    ]})
    client.get_range_config = AsyncMock(return_value={
        "ludus": [
            {"vm_name": "r-dc", "vlan": 10},
            {"vm_name": "r-kali", "vlan": 99},
        ],
        "network": {"inter_vlan_default": "ACCEPT",
                    "rules": [{"name": "kali to ad", "vlan_src": 99,
                               "vlan_dst": 10, "action": "ACCEPT"}]},
    })
    result = await NetworkAnalysisHandler(client).get_network_topology()

    assert result["status"] == "success", result
    topo = result["topology"]
    assert {n["vlan"] for n in topo["networks"]} == {10, 99}
    assert topo["inter_vlan_default"] == "ACCEPT"
    assert len(topo["inter_vlan_rules"]) == 1


@pytest.mark.asyncio
async def test_power_tools_send_the_machines_array(client):
    """The API needs a "machines" body array; a "vms" query param gave 409."""
    send = AsyncMock(return_value={"result": "ok"})
    with patch.object(client, "_send_request", send):
        await client.power_off_range()
    method, endpoint, body = send.await_args.args[:3]
    assert (method, endpoint) == ("PUT", "/range/poweroff")
    assert body == {"machines": ["all"]}


@pytest.mark.asyncio
async def test_power_tools_accept_named_vms(client):
    send = AsyncMock(return_value={"result": "ok"})
    with patch.object(client, "_send_request", send):
        await client.power_on_range(vms="r-dc,r-ws01")
    assert send.await_args.args[2] == {"machines": ["r-dc", "r-ws01"]}
    with patch.object(client, "_send_request", send):
        await client.power_on_range(vms=["r-dc"])
    assert send.await_args.args[2] == {"machines": ["r-dc"]}

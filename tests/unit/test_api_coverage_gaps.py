"""Tests for API surfaces that were missing or wrong, all confirmed live.

Every case here reproduces a real failure against Ludus 2.3.0:

* `get_console_ticket` sent `vmID`; the API reads `VMID` and returned HTTP 400
  "Invalid VMID" on every single call.
* `/vm/console/view` is a WebSocket upgrade, not a page -- an HTTP GET always
  returned 400 "Failed to upgrade connection to WebSocket".
* Blueprint `config` is YAML *text*; posting an object was rejected with
  "cannot unmarshal object into Go struct field ... of type string", and
  `update_blueprint_config` sent the config as the whole body instead of
  wrapping it in {"config": ...}.
* A 404 saying "implemented in a plugin that is not loaded" was flattened into
  "Resource not found", which reads as a wrong URL rather than an absent
  feature and sends callers hunting for a bug that isn't there.
"""

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.exceptions import LudusNotFoundError


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LUDUS_API_KEY", "k")
    monkeypatch.setenv("LUDUS_API_URL", "https://ludus.example:8080")
    monkeypatch.setenv("LUDUS_API_VERSION", "v2")
    import ludus_mcp.utils.config as config
    config._settings = None
    c = LudusAPIClient()
    c._server_verified = True
    c.api_version = "v2"
    yield c
    config._settings = None


# ---------- console ----------

@pytest.mark.asyncio
async def test_console_ticket_uses_uppercase_vmid(client):
    """Lowercase vmID returns HTTP 400 "Invalid VMID" on every call."""
    send = AsyncMock(return_value={"ticket": "t"})
    with patch.object(client, "_send_request", send):
        await client.get_console_ticket("106")

    params = send.await_args.args[3]
    assert params["VMID"] == "106"
    assert "vmID" not in params


@pytest.mark.asyncio
async def test_console_ticket_resolves_vm_name(client):
    """Every other VM tool takes names, so this one must too."""
    with patch.object(client, "resolve_vm_ids", AsyncMock(return_value=[106])):
        send = AsyncMock(return_value={"ticket": "t"})
        with patch.object(client, "_send_request", send):
            await client.get_console_ticket("tjnull-kali")

    assert send.await_args.args[3]["VMID"] == "106"


@pytest.mark.asyncio
async def test_console_ticket_unknown_name_raises(client):
    with patch.object(client, "resolve_vm_ids", AsyncMock(return_value=[])):
        with pytest.raises(LudusNotFoundError):
            await client.get_console_ticket("no-such-vm")


def test_console_view_url_is_websocket(client):
    """An HTTP GET here always 400s; return a URL to connect to instead."""
    result = client.build_console_view_url("abc def&=")

    assert result["protocol"] == "websocket"
    assert result["websocket_url"].startswith("wss://")
    # The ticket is percent-encoded, so & and = cannot split the query string.
    assert "abc%20def%26%3D" in result["websocket_url"]


# ---------- blueprint config is YAML text, not an object ----------

def test_config_as_yaml_converts_dict(client):
    out = client._config_as_yaml({"ludus": [{"vm_name": "a", "ram_gb": 2}]})
    assert isinstance(out, str)
    assert yaml.safe_load(out) == {"ludus": [{"vm_name": "a", "ram_gb": 2}]}


def test_config_as_yaml_passes_string_through(client):
    text = "ludus:\n- vm_name: a\n"
    assert client._config_as_yaml(text) == text


@pytest.mark.asyncio
async def test_create_blueprint_sends_config_as_string(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.create_blueprint("bp", {"ludus": [{"vm_name": "a"}]}, name="n")

    body = send.await_args.args[2]
    assert isinstance(body["config"], str), "object config is rejected by the API"
    assert yaml.safe_load(body["config"]) == {"ludus": [{"vm_name": "a"}]}
    assert body["blueprintID"] == "bp"


@pytest.mark.asyncio
async def test_create_blueprint_omits_unset_fields(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.create_blueprint("bp")

    assert send.await_args.args[2] == {"blueprintID": "bp"}


@pytest.mark.asyncio
async def test_update_blueprint_config_wraps_in_config_key(client):
    """Sending the config as the whole body silently loses it."""
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.update_blueprint_config("bp", {"ludus": [{"vm_name": "a"}]})

    body = send.await_args.args[2]
    assert set(body) == {"config"}
    assert yaml.safe_load(body["config"]) == {"ludus": [{"vm_name": "a"}]}


# ---------- 404 disambiguation ----------

def _status_error(status: int, body: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://ludus.example:8080/api/v2/user/quotas")
    response = httpx.Response(status, text=body, request=request)
    return httpx.HTTPStatusError("err", request=request, response=response)


@pytest.mark.asyncio
async def test_plugin_404_explains_feature_is_absent(client):
    body = '{"error":"This endpoint is implemented in a plugin that is not loaded"}'
    with patch.object(client.client, "request", AsyncMock(side_effect=_status_error(404, body))):
        with pytest.raises(LudusNotFoundError) as excinfo:
            await client._send_request("GET", "/user/quotas")

    message = str(excinfo.value)
    assert "plugin" in message
    assert "not available on this Ludus server" in message
    assert "Do not retry" in message


@pytest.mark.asyncio
async def test_ordinary_404_keeps_server_message(client):
    body = '{"error":"blueprint \\"nope\\" not found"}'
    with patch.object(client.client, "request", AsyncMock(side_effect=_status_error(404, body))):
        with pytest.raises(LudusNotFoundError) as excinfo:
            await client._send_request("GET", "/blueprints/nope")

    assert 'blueprint "nope" not found' in str(excinfo.value)


# ---------- non-JSON responses ----------

@pytest.mark.asyncio
async def test_non_json_body_does_not_raise(client):
    """/openapi serves YAML; calling .json() on it used to explode."""
    response = httpx.Response(
        200,
        text="openapi: 3.0.0\n",
        headers={"content-type": "text/yaml"},
        request=httpx.Request("GET", "https://ludus.example:8080/api/v2/openapi"),
    )
    with patch.object(client.client, "request", AsyncMock(return_value=response)):
        result = await client._send_request("GET", "/openapi")

    assert result["text"] == "openapi: 3.0.0\n"
    assert result["content_type"] == "text/yaml"


@pytest.mark.asyncio
async def test_raw_returns_bytes_for_binary_endpoints(client):
    """Blueprint export serves gzip, which must not be decoded as JSON."""
    payload = b"\x1f\x8b\x08\x00binary"
    response = httpx.Response(
        200,
        content=payload,
        headers={"content-type": "application/gzip"},
        request=httpx.Request("GET", "https://ludus.example:8080/api/v2/blueprints/x/export"),
    )
    with patch.object(client.client, "request", AsyncMock(return_value=response)):
        result = await client._send_request("GET", "/blueprints/x/export", raw=True)

    assert result["content"] == payload
    assert result["size_bytes"] == len(payload)


@pytest.mark.asyncio
async def test_export_blueprint_writes_archive(client, tmp_path):
    payload = b"\x1f\x8b\x08\x00archive-bytes"
    out = tmp_path / "nested" / "bp.tar.gz"
    with patch.object(
        client, "_request", AsyncMock(return_value={"content": payload, "size_bytes": len(payload)})
    ):
        result = await client.export_blueprint("bp", str(out))

    assert out.read_bytes() == payload
    assert result["size_bytes"] == len(payload)


# ---------- quota payloads ----------

@pytest.mark.asyncio
async def test_set_user_quotas_omits_unset_values(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.set_user_quotas(["u1"], quota_ram=32768)

    assert send.await_args.args[2] == {"userIDs": ["u1"], "quotaRAM": 32768}


@pytest.mark.asyncio
async def test_set_user_quotas_rejects_empty_user_list(client):
    with pytest.raises(ValueError):
        await client.set_user_quotas([], quota_ram=1)


@pytest.mark.asyncio
async def test_set_group_quotas_omits_unset_values(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.set_group_quotas(["students"], default_quota_vms=5)

    assert send.await_args.args[2] == {"groupNames": ["students"], "defaultQuotaVMs": 5}


@pytest.mark.asyncio
async def test_set_auto_shutdown_rejects_negative_timeout(client):
    with pytest.raises(ValueError):
        await client.set_auto_shutdown(-1)


@pytest.mark.asyncio
async def test_set_auto_shutdown_allows_zero_to_disable(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.set_auto_shutdown(0)

    assert send.await_args.args[2] == {"autoShutdownTimeout": 0}


# ---------- source uploads ----------

@pytest.mark.asyncio
async def test_add_source_requires_url_for_git(client):
    with pytest.raises(ValueError):
        await client.add_source("s", source_type="git")


@pytest.mark.asyncio
async def test_add_source_requires_archive_for_archive_type(client):
    with pytest.raises(ValueError):
        await client.add_source("s", source_type="archive")


@pytest.mark.asyncio
async def test_add_source_sends_multipart_form(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.add_source("s", url="https://example.com/repo.git", ref="main")

    form = send.await_args.args[5]
    assert form["id"] == "s"
    assert form["url"] == "https://example.com/repo.git"
    assert form["ref"] == "main"
    # Go parses these from form values, so booleans must be lowercase strings.
    assert form["global"] == "false"


@pytest.mark.asyncio
async def test_add_source_rejects_missing_archive_file(client, tmp_path):
    with pytest.raises(ValueError, match="Archive not found"):
        await client.add_source(
            "s", source_type="archive", archive_path=str(tmp_path / "nope.tar.gz")
        )


# ---------- 501: permanent, not a retryable server error ----------

@pytest.mark.asyncio
async def test_501_is_not_reported_as_retryable(client):
    """/range/sshconfig returns 501; "try again later" sends callers in circles."""
    body = '{"error":"Not implemented"}'
    with patch.object(client.client, "request", AsyncMock(side_effect=_status_error(501, body))):
        with pytest.raises(LudusNotFoundError) as excinfo:
            await client._send_request("GET", "/range/sshconfig")

    message = str(excinfo.value)
    assert "not implemented" in message.lower()
    assert "Retrying will not help" in message
    assert "try again later" not in message.lower()


@pytest.mark.asyncio
async def test_genuine_5xx_is_still_retryable_server_error(client):
    from ludus_mcp.exceptions import LudusServerError

    with patch.object(
        client.client, "request", AsyncMock(side_effect=_status_error(500, '{"error":"boom"}'))
    ):
        with pytest.raises(LudusServerError):
            await client._send_request("GET", "/range")


@pytest.mark.asyncio
async def test_documentation_survives_missing_ssh_config():
    """SSH config is one section; losing it must not discard the whole document."""
    from ludus_mcp.server.handlers.documentation import DocumentationHandler

    fake = MagicMock()
    fake.get_range = AsyncMock(return_value={"rangeState": "SUCCESS", "VMs": [{"name": "dc"}]})
    fake.get_range_config = AsyncMock(return_value={"ludus": [{"vm_name": "dc"}]})
    fake.get_range_sshconfig = AsyncMock(side_effect=LudusNotFoundError("501 not implemented"))

    result = await DocumentationHandler(fake).generate_range_documentation()

    assert result["status"] == "success"
    assert result["vm_count"] == 1
    assert "not available" in result["documentation"]

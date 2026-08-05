"""Tests for requests whose shape was wrong, each confirmed against Ludus 2.3.0.

These were not "the endpoint 404s" bugs -- the calls were accepted and appeared
to work, which is what made them dangerous:

* deploy_range put tags/limit/only_roles/force in the query string. The API
  reads them from the body, so every filter was silently dropped and a request
  meant to touch one VM redeployed the whole range.
* move_role_scope sent {"name", "scope"}; the API wants {"roles": [...],
  "global": bool} and rejected every call with "At least one role name is
  required".
* add_template posted JSON to /templates/add, which does not exist. Templates
  are uploaded as an uncompressed tar to PUT /templates -- a gzipped one is
  rejected with "Invalid tar archive: unexpected EOF".
* The access handler called .get() on get_range_access(), which returns a list
  on v2, so granting range access raised AttributeError every time.
"""

import io
import tarfile

import pytest
from unittest.mock import AsyncMock, patch

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.handlers.access import AccessHandler


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


# ---------- deploy filters belong in the body ----------

@pytest.mark.asyncio
async def test_deploy_filters_go_in_body_not_query(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.deploy_range(tags="user,domain", limit="DC*", only_roles="r1", force=True)

    _method, _endpoint, body, params = send.await_args.args[:4]
    assert body == {
        "tags": "user,domain",
        "limit": "DC*",
        "only_roles": "r1",
        "force": True,
    }
    # A filter left in the query is ignored by the server -- the whole range deploys.
    assert params == {}


@pytest.mark.asyncio
async def test_deploy_sends_only_range_and_user_as_query(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.deploy_range(user_id="jdoe", range_id="7", limit="DC*")

    _method, _endpoint, body, params = send.await_args.args[:4]
    assert params == {"userID": "jdoe", "rangeID": "7"}
    assert body == {"limit": "DC*"}


@pytest.mark.asyncio
async def test_deploy_with_no_filters_sends_no_body(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.deploy_range()

    assert send.await_args.args[2] is None


@pytest.mark.asyncio
async def test_deploy_with_config_stores_it_first(client):
    """/range/deploy has no config field; it deploys whatever is stored."""
    config = {"ludus": [{"vm_name": "a"}]}
    update = AsyncMock(return_value={})
    send = AsyncMock(return_value={})
    with patch.object(client, "update_range_config", update):
        with patch.object(client, "_send_request", send):
            await client.deploy_range(config=config, tags="user")

    update.assert_awaited_once_with(config, None)
    assert send.await_args.args[2] == {"tags": "user"}


# ---------- role scope ----------

@pytest.mark.asyncio
async def test_move_role_scope_sends_roles_array_and_global(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.move_role_scope("badsectorlabs.ludus_adcs", "global")

    assert send.await_args.args[2] == {
        "roles": ["badsectorlabs.ludus_adcs"],
        "global": True,
    }


@pytest.mark.asyncio
async def test_move_role_scope_user_scope_is_not_global(client):
    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.move_role_scope(["a.b", "c.d"], "user", copy=True)

    assert send.await_args.args[2] == {
        "roles": ["a.b", "c.d"],
        "global": False,
        "copy": True,
    }


@pytest.mark.asyncio
async def test_move_role_scope_rejects_unknown_scope(client):
    with pytest.raises(ValueError, match="Unknown scope"):
        await client.move_role_scope("a.b", "somewhere-else")


@pytest.mark.asyncio
async def test_move_role_scope_rejects_empty_roles(client):
    with pytest.raises(ValueError):
        await client.move_role_scope([])


# ---------- template upload ----------

@pytest.mark.asyncio
async def test_add_template_uploads_uncompressed_tar(client, tmp_path):
    template_dir = tmp_path / "my-template"
    template_dir.mkdir()
    (template_dir / "my-template.pkr.hcl").write_text("# packer\n")

    send = AsyncMock(return_value={})
    with patch.object(client, "_send_request", send):
        await client.add_template(str(template_dir), force=True)

    method, endpoint = send.await_args.args[:2]
    files, data = send.await_args.args[4], send.await_args.args[5]
    assert (method, endpoint) == ("PUT", "/templates")
    assert data == {"force": "true"}

    name, payload, content_type = files["file"]
    assert name.endswith(".tar") and not name.endswith(".gz")
    assert content_type == "application/x-tar"

    # A gzipped archive is rejected; this must be a readable plain tar.
    with tarfile.open(fileobj=io.BytesIO(payload)) as tar:
        assert "my-template/my-template.pkr.hcl" in tar.getnames()


@pytest.mark.asyncio
async def test_add_template_rejects_missing_directory(client, tmp_path):
    with pytest.raises(ValueError, match="Template directory not found"):
        await client.add_template(str(tmp_path / "nope"))


# ---------- range access on v2 ----------

@pytest.fixture
def access(client):
    return AccessHandler(client)


@pytest.mark.asyncio
async def test_grant_range_access_uses_assign_endpoint(access, client):
    """v2 returns a LIST of accessible ranges; .get() on it raised AttributeError."""
    with patch.object(client, "get_range", AsyncMock(return_value={"rangeID": "tjnull"})):
        with patch.object(
            client, "list_range_users",
            AsyncMock(side_effect=[[{"userID": "tjnull"}], [{"userID": "tjnull"}, {"userID": "lazarus"}]]),
        ):
            assign = AsyncMock(return_value={})
            with patch.object(client, "assign_range_to_user", assign):
                result = await access.grant_range_access(users=["lazarus"])

    assign.assert_awaited_once_with("lazarus", "tjnull")
    assert result["granted"] == ["lazarus"]
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_grant_skips_users_who_already_have_access(access, client):
    with patch.object(client, "get_range", AsyncMock(return_value={"rangeID": "tjnull"})):
        with patch.object(
            client, "list_range_users", AsyncMock(return_value=[{"userID": "lazarus"}])
        ):
            assign = AsyncMock(return_value={})
            with patch.object(client, "assign_range_to_user", assign):
                result = await access.grant_range_access(users=["lazarus"])

    assign.assert_not_awaited()
    assert result["already_had_access"] == ["lazarus"]


@pytest.mark.asyncio
async def test_revoke_range_access_uses_revoke_endpoint(access, client):
    with patch.object(client, "get_range", AsyncMock(return_value={"rangeID": "tjnull"})):
        with patch.object(
            client, "list_range_users",
            AsyncMock(side_effect=[[{"userID": "lazarus"}], []]),
        ):
            revoke = AsyncMock(return_value={})
            with patch.object(client, "revoke_range_from_user", revoke):
                result = await access.revoke_range_access(users=["lazarus"])

    revoke.assert_awaited_once_with("lazarus", "tjnull")
    assert result["revoked"] == ["lazarus"]


@pytest.mark.asyncio
async def test_set_range_access_grants_and_revokes_to_match(access, client):
    with patch.object(client, "get_range", AsyncMock(return_value={"rangeID": "tjnull"})):
        with patch.object(
            client, "list_range_users",
            AsyncMock(side_effect=[[{"userID": "old"}], [{"userID": "new"}]]),
        ):
            assign, revoke = AsyncMock(return_value={}), AsyncMock(return_value={})
            with patch.object(client, "assign_range_to_user", assign):
                with patch.object(client, "revoke_range_from_user", revoke):
                    result = await access.set_range_access(users=["new"])

    assign.assert_awaited_once_with("new", "tjnull")
    revoke.assert_awaited_once_with("old", "tjnull")
    assert result["granted"] == ["new"] and result["revoked"] == ["old"]


@pytest.mark.asyncio
async def test_access_errors_are_reported_per_user(access, client):
    with patch.object(client, "get_range", AsyncMock(return_value={"rangeID": "tjnull"})):
        with patch.object(client, "list_range_users", AsyncMock(return_value=[])):
            with patch.object(
                client, "assign_range_to_user", AsyncMock(side_effect=RuntimeError("boom"))
            ):
                result = await access.grant_range_access(users=["lazarus"])

    assert result["status"] == "error"
    assert result["errors"][0]["userID"] == "lazarus"
    assert "boom" in result["errors"][0]["error"]

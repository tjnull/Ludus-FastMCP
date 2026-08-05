"""Tests for AD group/user consistency in scenario configs.

A user assigned to a group nothing creates fails the deploy on the domain
controller with "Failed to find the AD object DNs for groups.set. Invalid
identities" - roughly an hour into a deployment, naming the user rather than
the group. These checks catch it at build/validate time instead.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ludus_mcp.scenarios.base import BaseScenarioBuilder
from ludus_mcp.server.handlers.validation import ValidationHandler


def _config_with(users, groups, ous=None):
    return {
        "ludus": [
            {
                "vm_name": "r-dc", "hostname": "DC01",
                "template": "win2022-server-x64-template",
                "vlan": 10, "ip_last_octet": 10, "ram_gb": 8, "cpus": 4,
                "windows": {"sysprep": False},
                "role_vars": {"ludus_ad": {"domain": "corp.local",
                                           "ous": ous or [],
                                           "groups": groups,
                                           "users": users}},
            }
        ]
    }


@pytest.fixture
def handler():
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[{"name": "win2022-server-x64-template"}])
    return ValidationHandler(client)


@pytest.mark.asyncio
async def test_flags_group_that_is_never_created(handler):
    config = _config_with(
        users=[{"name": "jane.doe", "groups": ["Domain Users", "HR Managers"]}],
        groups=[{"name": "HR Department"}],
    )
    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    messages = " ".join(getattr(e, "message", str(e)) for e in data["errors"])
    assert data["valid"] is False
    assert "HR Managers" in messages
    assert "jane.doe" in messages


@pytest.mark.asyncio
async def test_builtin_groups_are_not_flagged(handler):
    """These exist in a fresh AD; assigning users to them is legitimate."""
    config = _config_with(
        users=[{"name": "jane.doe",
                "groups": ["Domain Users", "Backup Operators",
                           "Remote Desktop Users", "IIS_IUSRS"]}],
        groups=[],
    )
    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    ad_errors = [e for e in data["errors"] if "ludus_ad" in getattr(e, "field", "")]
    assert ad_errors == []


@pytest.mark.asyncio
async def test_defined_groups_pass(handler):
    config = _config_with(
        users=[{"name": "jane.doe", "groups": ["Domain Users", "HR Managers"]}],
        groups=[{"name": "HR Managers"}],
    )
    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    ad_errors = [e for e in data["errors"] if "ludus_ad" in getattr(e, "field", "")]
    assert ad_errors == []


class _Builder(BaseScenarioBuilder):
    def build(self):  # pragma: no cover - not used
        pass


def test_builder_creates_groups_its_users_reference():
    """to_dict() reconciles referenced groups for every builder, not just some."""
    b = _Builder()
    b.add_vm(
        vm_name="r-dc", hostname="DC01", template="win2022-server-x64-template",
        vlan=10, ip_last_octet=10,
        role_vars={"ludus_ad": {
            "domain": "corp.local",
            "ous": [{"name": "HR"}],
            "groups": [{"name": "Domain Users"}],
            "users": [{"name": "jane.doe", "groups": ["Domain Users", "HR Managers",
                                                      "Backup Operators"]}],
        }},
    )
    cfg = b.to_dict()
    groups = {g["name"] for g in cfg["ludus"][0]["role_vars"]["ludus_ad"]["groups"]}
    assert "HR Managers" in groups, "referenced group must be created"
    assert "Backup Operators" not in groups, "built-ins must not be re-created"
    hr = next(g for g in cfg["ludus"][0]["role_vars"]["ludus_ad"]["groups"]
              if g["name"] == "HR Managers")
    assert hr["path"] == "OU=HR,DC=corp,DC=local"


def test_windows_vms_default_to_sysprep_true():
    """Identical machine SIDs break the second domain join."""
    b = _Builder()
    b.add_vm(vm_name="r-fs", hostname="FILES01",
             template="win2022-server-x64-template", vlan=10, ip_last_octet=15)
    b.add_vm(vm_name="r-kali", hostname="KALI",
             template="kali-x64-desktop-template", vlan=99, ip_last_octet=10)
    vms = b.to_dict()["ludus"]
    assert vms[0]["windows"] == {"sysprep": True}
    assert vms[1]["linux"] is True


def test_colliding_windows_hostnames_are_rewritten():
    """{{ range_id }}-BLUE-WS01/02 truncate to the same NetBIOS name."""
    b = _Builder()
    for i in (1, 2):
        b.add_vm(vm_name=f"r-ws{i}", hostname=f"{{{{ range_id }}}}-BLUE-WS0{i}",
                 template="win2022-server-x64-template", vlan=10, ip_last_octet=20 + i)
    names = [vm["hostname"] for vm in b.to_dict()["ludus"]]
    truncated = [n.replace("{{ range_id }}", "tjnull")[:15] for n in names]
    assert len(set(truncated)) == 2, f"still colliding: {names}"


def test_non_colliding_hostnames_are_left_alone():
    b = _Builder()
    b.add_vm(vm_name="r-dc", hostname="{{ range_id }}-DC01",
             template="win2022-server-x64-template", vlan=10, ip_last_octet=10)
    b.add_vm(vm_name="r-fs", hostname="{{ range_id }}-FILES01",
             template="win2022-server-x64-template", vlan=10, ip_last_octet=15)
    names = [vm["hostname"] for vm in b.to_dict()["ludus"]]
    assert names == ["{{ range_id }}-DC01", "{{ range_id }}-FILES01"]


@pytest.mark.asyncio
async def test_validation_flags_hostname_collisions(handler):
    config = {"ludus": [
        {"vm_name": "a", "hostname": "{{ range_id }}-BLUE-WS01",
         "template": "win2022-server-x64-template", "vlan": 10,
         "ip_last_octet": 21, "ram_gb": 4, "cpus": 2, "windows": {"sysprep": True}},
        {"vm_name": "b", "hostname": "{{ range_id }}-BLUE-WS02",
         "template": "win2022-server-x64-template", "vlan": 10,
         "ip_last_octet": 22, "ram_gb": 4, "cpus": 2, "windows": {"sysprep": True}},
    ]}
    result = await handler.validate_config(config)
    data = result if isinstance(result, dict) else result.__dict__
    messages = " ".join(getattr(e, "message", str(e)) for e in data["errors"])
    assert data["valid"] is False
    assert "truncated to 15" in messages

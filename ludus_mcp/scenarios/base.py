"""Base scenario builder for Ludus range configurations."""

from typing import Any
import yaml
from .siem_config import (
    SIEMType,
    get_siem_server_config,
    add_siem_agent_to_vm,
    get_siem_network_rules,
)
from ..schemas.scenario_customization import ScenarioCustomization


class BaseScenarioBuilder:
    """Base class for building Ludus range scenarios."""

    def __init__(
        self,
        range_id: str = "{{ range_id }}",
        siem_type: SIEMType = "wazuh",
        resource_profile: str = "minimal",
        customization: ScenarioCustomization | None = None,
        randomize: bool = False,
    ):
        """Initialize the scenario builder.

        Args:
            range_id: Range identifier
            siem_type: SIEM type (wazuh, splunk, elastic, security-onion, none)
            resource_profile: Resource allocation profile - "minimal", "recommended", "maximum"
                - minimal: Lowest resource requirements (may be slow)
                - recommended: Balanced performance and resource usage (default)
                - maximum: High performance with maximum resources
            customization: Optional scenario customization (users, vulnerabilities, etc.)
            randomize: Whether to apply randomization (requires customization with randomization_config)
        """
        self.range_id = range_id
        self.siem_type = siem_type
        self.resource_profile = resource_profile
        self.customization = customization
        self.randomize = randomize
        self.config = {
            "name": None,  # Range name - will be set by scenario builders
            "ludus": [],
            "network": {
                "inter_vlan_default": "REJECT",
                "rules": [],
            },
        }

        # Resource profiles: (ram_gb, cpus)
        self.RESOURCE_PROFILES = {
            "minimal": {
                "dc": (2, 2),
                "workstation": (2, 2),
                "server": (2, 2),
                "sql_server": (4, 2),
                "exchange_server": (4, 2),
                "kali": (4, 2),
                "siem": (4, 2),
                "edr": (4, 2),
                "linux_server": (2, 2),
                "analysis_win": (4, 2),
                "analysis_linux": (4, 2),
            },
            "recommended": {
                "dc": (4, 2),
                "workstation": (4, 2),
                "server": (4, 2),
                "sql_server": (8, 4),
                "exchange_server": (8, 4),
                "kali": (8, 4),
                "siem": (8, 4),
                "edr": (6, 2),
                "linux_server": (4, 2),
                "analysis_win": (8, 4),
                "analysis_linux": (8, 4),
            },
            "maximum": {
                "dc": (8, 4),
                "workstation": (8, 4),
                "server": (8, 4),
                "sql_server": (16, 8),
                "exchange_server": (16, 8),
                "kali": (16, 8),
                "siem": (16, 8),
                "edr": (12, 4),
                "linux_server": (8, 4),
                "analysis_win": (16, 8),
                "analysis_linux": (16, 8),
            },
        }

    def get_resources(self, vm_type: str) -> tuple[int, int]:
        """Get RAM and CPU allocation for a VM type based on resource profile.

        Args:
            vm_type: Type of VM (dc, workstation, server, etc.)

        Returns:
            Tuple of (ram_gb, cpus)
        """
        profile = self.RESOURCE_PROFILES.get(self.resource_profile, self.RESOURCE_PROFILES["minimal"])
        return profile.get(vm_type, (2, 2))  # Default to 2GB/2CPU if type not found

    def add_vm(
        self,
        vm_name: str,
        hostname: str,
        template: str,
        vlan: int,
        ip_last_octet: int,
        ram_gb: int = 8,
        cpus: int = 4,
        **kwargs: Any,
    ) -> None:
        """Add a VM to the configuration."""
        vm_config: dict[str, Any] = {
            "vm_name": vm_name,
            "hostname": hostname,
            "template": template,
            "vlan": vlan,
            "ip_last_octet": ip_last_octet,
            "ram_gb": ram_gb,
            "cpus": cpus,
        }
        vm_config.update(kwargs)

        # Ludus's schema requires each VM to declare exactly one of "windows" or
        # "linux" (oneOf). Builders frequently omitted both, and Ludus rejected
        # the whole config with "ludus.N: windows is required" - which named an
        # index rather than the VM, making it painful to trace. Infer it from the
        # template when the caller did not say.
        if "windows" not in vm_config and "linux" not in vm_config:
            if "win" in template.lower():
                # sysprep MUST default to True: every Windows VM cloned from the
                # same template otherwise shares a machine SID, and the second one
                # to join the domain fails with "the SID of the domain you
                # attempted to join was identical to the SID of this machine".
                # Ludus's own GOAD blueprint sets sysprep: true on every Windows
                # host except the first domain controller.
                vm_config["windows"] = {"sysprep": True}
            else:
                vm_config["linux"] = True

        self.config["ludus"].append(vm_config)

    def add_network_rule(
        self,
        name: str,
        vlan_src: int,
        vlan_dst: int,
        protocol: str = "all",
        ports: str | int = "all",
        action: str = "ACCEPT",
    ) -> None:
        """Add a network rule."""
        rule = {
            "name": name,
            "vlan_src": vlan_src,
            "vlan_dst": vlan_dst,
            "protocol": protocol,
            "ports": ports,
            "action": action,
        }
        self.config["network"]["rules"].append(rule)

    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        # Add YAML schema comment
        yaml_str = "# yaml-language-server: $schema=https://docs.ludus.cloud/schemas/range-config.json\n\n"
        yaml_str += yaml.dump(self.config, default_flow_style=False, sort_keys=False)
        return yaml_str

    def add_siem_server(
        self, vlan: int = 10, ip_last_octet: int = 100, siem_type: SIEMType | None = None
    ) -> dict[str, Any]:
        """Add SIEM server to the configuration."""
        if siem_type is None:
            siem_type = self.siem_type
        
        if siem_type == "none":
            return {}
        
        siem_config = get_siem_server_config(siem_type, self.range_id, vlan, ip_last_octet)
        self.add_vm(**siem_config)
        
        # Add SIEM network rules
        for rule in get_siem_network_rules(siem_type):
            # Convert 0 (all VLANs) to actual VLAN numbers for each rule
            if rule["vlan_src"] == 0:
                # Allow from all existing VLANs in the config
                existing_vlans = set()
                for vm in self.config["ludus"]:
                    if "vlan" in vm:
                        existing_vlans.add(vm["vlan"])
                # Add rules for each VLAN to SIEM server VLAN
                for src_vlan in existing_vlans:
                    self.add_network_rule(
                        name=rule["name"] + f" (from VLAN {src_vlan})",
                        vlan_src=src_vlan,
                        vlan_dst=vlan,
                        protocol=rule["protocol"],
                        ports=rule["ports"],
                        action=rule["action"],
                    )
            else:
                self.add_network_rule(**rule)
        
        return siem_config

    def _siem_server_address(self, siem_keyword: str) -> str:
        """Ludus range address of the SIEM server VM, in template form.

        Ludus expands "{{ range_second_octet }}" per range, so the address stays
        correct whichever range the config is deployed into.
        """
        for vm in self.config.get("ludus", []):
            name = str(vm.get("vm_name", "")).lower()
            if siem_keyword and siem_keyword in name and "server" in name:
                vlan = vm.get("vlan", 10)
                octet = vm.get("ip_last_octet", 100)
                return f"10.{{{{ range_second_octet }}}}.{vlan}.{octet}"
        # No SIEM server in this range: fall back to the conventional slot
        return "10.{{ range_second_octet }}.10.100"

    def add_siem_agents_to_all_vms(self, siem_server_ip: str | None = None, siem_type: SIEMType | None = None) -> None:
        """Add SIEM agent configuration to all VMs in the range."""
        if siem_type is None:
            siem_type = self.siem_type
        
        if siem_type == "none":
            return
        
        siem_keywords = {
            "wazuh": "wazuh",
            "splunk": "splunk",
            "elastic": "elastic",
            "security-onion": "security-onion",
        }
        
        siem_keyword = siem_keywords.get(siem_type, "")

        # Derive the SIEM server's address from the VM that actually hosts it.
        # This used to default to a hardcoded 192.168.10.100 "to be replaced with
        # actual IP" - which never happened, so every agent was pointed at an
        # address outside the range and could never register.
        if siem_server_ip is None:
            siem_server_ip = self._siem_server_address(siem_keyword)

        for vm in self.config["ludus"]:
            # Skip SIEM server itself
            if siem_keyword in vm.get("vm_name", "").lower() and "server" in vm.get("vm_name", "").lower():
                continue
            
            # Add SIEM agent to all other VMs
            add_siem_agent_to_vm(vm, siem_type, siem_server_ip)
    
    # Backward compatibility methods
    def add_wazuh_server(self, vlan: int = 10, ip_last_octet: int = 100) -> dict[str, Any]:
        """Add Wazuh server (backward compatibility)."""
        return self.add_siem_server(vlan, ip_last_octet, "wazuh")
    
    def add_wazuh_agent_to_all_vms(self, wazuh_server_ip: str | None = None) -> None:
        """Add Wazuh agents (backward compatibility)."""
        self.add_siem_agents_to_all_vms(wazuh_server_ip, "wazuh")

    def set_range_name(self, name: str) -> "BaseScenarioBuilder":
        """Set the range name.
        
        Args:
            name: Range name to set
            
        Returns:
            Self for method chaining
        """
        self.config["name"] = name
        return self
    
    def apply_customizations(self) -> None:
        """Apply customizations to the configuration.
        
        This method should be called after the scenario is built but before finalizing.
        """
        if not self.customization:
            return
        
        # Apply network customizations
        if self.customization.network_customization:
            nc = self.customization.network_customization
            if nc.inter_vlan_default:
                self.config["network"]["inter_vlan_default"] = nc.inter_vlan_default
            
            # Apply VLAN changes
            if nc.vlan_changes:
                for vm in self.config.get("ludus", []):
                    vm_name = vm.get("vm_name", "")
                    for pattern, new_vlan in nc.vlan_changes.items():
                        if pattern in vm_name:
                            vm["vlan"] = new_vlan
            
            # Add additional rules
            if nc.additional_rules:
                self.config["network"]["rules"].extend(nc.additional_rules)
            
            # Remove rules
            if nc.remove_rules:
                self.config["network"]["rules"] = [
                    rule for rule in self.config["network"]["rules"]
                    if rule.get("name") not in nc.remove_rules
                ]
        
        # Apply VM customizations
        if self.customization.vm_customization:
            vc = self.customization.vm_customization
            
            # Apply resource overrides
            if vc.resource_overrides:
                for vm in self.config.get("ludus", []):
                    vm_name = vm.get("vm_name", "")
                    if vm_name in vc.resource_overrides:
                        overrides = vc.resource_overrides[vm_name]
                        if "ram_gb" in overrides:
                            vm["ram_gb"] = overrides["ram_gb"]
                        if "cpus" in overrides:
                            vm["cpus"] = overrides["cpus"]
            
            # Remove VMs
            if vc.remove_vms:
                self.config["ludus"] = [
                    vm for vm in self.config["ludus"]
                    if not any(pattern in vm.get("vm_name", "") for pattern in vc.remove_vms)
                ]
            
            # Add additional VMs
            if vc.additional_vms:
                self.config["ludus"].extend(vc.additional_vms)
    
    def to_dict(self) -> dict[str, Any]:
        """Get configuration as dictionary.
        
        Converts ansible_roles format to Ludus roles format:
        - ansible_roles: [{name: "...", vars: {...}}] -> roles: ["..."] and role_vars: {...}
        
        Also applies any customizations before returning.
        """
        # Apply customizations before converting
        self.apply_customizations()
        
        config = self.config.copy()
        
        # Ensure name is set (use default if None)
        if config.get("name") is None:
            config["name"] = "Ludus Range"
        
        # Convert ansible_roles to Ludus format (roles + role_vars)
        for vm in config.get("ludus", []):
            if "ansible_roles" in vm:
                ansible_roles = vm.pop("ansible_roles")
                
                # Extract role names for 'roles' array
                roles_list = []
                role_vars_dict = {}
                
                for role in ansible_roles:
                    if isinstance(role, dict):
                        role_name = role.get("name")
                        if role_name:
                            roles_list.append(role_name)
                            # Merge role-specific vars into role_vars
                            role_vars = role.get("vars", {})
                            if role_vars:
                                # Prefix role vars with role name to avoid conflicts
                                # Or merge directly if no conflicts
                                for key, value in role_vars.items():
                                    if key not in role_vars_dict:
                                        role_vars_dict[key] = value
                                    elif isinstance(role_vars_dict[key], dict) and isinstance(value, dict):
                                        role_vars_dict[key].update(value)
                    elif isinstance(role, str):
                        roles_list.append(role)
                
                if roles_list:
                    vm["roles"] = roles_list
                if role_vars_dict:
                    vm["role_vars"] = role_vars_dict

        self._ensure_referenced_ad_groups_exist(config)
        self._ensure_unique_windows_hostnames(config)

        return config

    # Windows NetBIOS names are capped at 15 characters, and Ludus rejects a
    # config whose Windows hostnames collide once truncated to that length.
    NETBIOS_MAX = 15

    def _ensure_unique_windows_hostnames(self, config: dict[str, Any]) -> None:
        """Keep Windows hostnames unique within the first 15 characters.

        Hostnames were built as "{{ range_id }}-BLUE-WS01"; with a range ID of
        any realistic length the distinguishing digits fall past character 15,
        so "...-BLUE-WS01" and "...-BLUE-WS02" both truncate to the same name
        and Ludus refuses the config with "duplicate Windows hostname name
        found". Dropping the range-ID prefix reclaims those characters - Ludus
        already scopes hostnames per range, and its own GOAD blueprint uses bare
        hostnames for exactly this reason.
        """
        vms = [vm for vm in config.get("ludus", []) or []
               if isinstance(vm, dict) and "win" in str(vm.get("template", "")).lower()]
        if not vms:
            return

        def truncated(name: str, range_id: str = "rangeid") -> str:
            return name.replace("{{ range_id }}", range_id)[: self.NETBIOS_MAX]

        # Only rewrite when the prefix actually causes a collision
        seen: dict[str, int] = {}
        for vm in vms:
            seen[truncated(str(vm.get("hostname", "")))] = seen.get(
                truncated(str(vm.get("hostname", ""))), 0) + 1
        if not any(count > 1 for count in seen.values()):
            return

        used: set[str] = set()
        for vm in vms:
            hostname = str(vm.get("hostname", ""))
            stripped = hostname.replace("{{ range_id }}-", "").replace("{{ range_id }}", "")
            candidate = (stripped or hostname)[: self.NETBIOS_MAX]
            if candidate in used:
                # Still colliding: replace the tail with a counter
                for n in range(1, 100):
                    suffix = str(n)
                    trimmed = candidate[: self.NETBIOS_MAX - len(suffix)] + suffix
                    if trimmed not in used:
                        candidate = trimmed
                        break
            used.add(candidate)
            vm["hostname"] = candidate

    # Groups that a fresh AD install already provides; creating them errors,
    # but users may be assigned to them.
    AD_BUILTIN_GROUPS = frozenset({
        "Domain Users", "Domain Admins", "Domain Guests", "Domain Computers",
        "Enterprise Admins", "Schema Admins", "Administrators", "Users", "Guests",
        "Power Users", "Backup Operators", "Remote Desktop Users", "IIS_IUSRS",
        "Print Operators", "Server Operators", "Account Operators",
        "Group Policy Creator Owners", "Protected Users", "Remote Management Users",
    })

    def _ensure_referenced_ad_groups_exist(self, config: dict[str, Any]) -> None:
        """Create any AD group a user is assigned to but nothing defines.

        Builders derive groups in their own ways and several missed some, which
        only surfaced an hour into a deployment as
        "Failed to find the AD object DNs for groups.set. Invalid identities".
        Reconciling here covers every builder, including future ones.
        """
        for vm in config.get("ludus", []) or []:
            if not isinstance(vm, dict):
                continue
            ad = (vm.get("role_vars") or {}).get("ludus_ad")
            if not isinstance(ad, dict):
                continue

            groups = ad.setdefault("groups", [])
            defined = {g.get("name") for g in groups if isinstance(g, dict)}
            defined |= {g for g in groups if isinstance(g, str)}
            ou_names = {
                o.get("name") for o in (ad.get("ous") or []) if isinstance(o, dict)
            }

            referenced: list[str] = []
            for user in ad.get("users") or []:
                if not isinstance(user, dict):
                    continue
                user_groups = user.get("groups") or []
                if isinstance(user_groups, str):
                    user_groups = [user_groups]
                referenced.extend(user_groups)

            domain = ad.get("domain") or "corp.local"
            base_dn = ",".join(f"DC={part}" for part in str(domain).split("."))

            for name in sorted(set(referenced)):
                if not name or name in defined or name in self.AD_BUILTIN_GROUPS:
                    continue
                path = base_dn
                if "Managers" in name:
                    dept = name.replace("Managers", "").strip()
                    if dept in ou_names:
                        path = f"OU={dept},{base_dn}"
                elif name in ou_names:
                    path = f"OU={name},{base_dn}"
                groups.append({
                    "name": name,
                    "scope": "global",
                    "path": path,
                    "description": f"{name} group",
                })
                defined.add(name)


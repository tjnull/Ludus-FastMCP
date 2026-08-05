"""Red team offensive security scenarios - realistic enterprise attack simulations."""

from .base import BaseScenarioBuilder
from .ad_config import (
    get_realistic_ad_users,
    get_local_admin_accounts,
    get_ad_cs_config,
    get_ad_attack_paths,
)
from .wazuh_opsec import get_wazuh_opsec_ansible_vars


class RedTeamScenarioBuilder(BaseScenarioBuilder):
    """Builder for red team offensive security scenarios."""

    def build_redteam_lab_lite(self) -> "RedTeamScenarioBuilder":
        """Build lite red team lab - Small business environment.

        Realistic scenario: Small business with basic AD setup
        - Single domain controller
        - 2 Windows workstations (employee machines)
        - 1 File server (shared documents)
        - Kali attacker machine

        Attack scenarios:
        - Initial access via phishing/vulnerable services
        - Credential harvesting
        - Basic lateral movement
        - File server compromise
        - Domain privilege escalation

        Resource requirements (by profile):
        - Minimal: 14GB RAM, 12 CPUs (may be slow)
        - Recommended: 24GB RAM, 12 CPUs (default)
        - Maximum: 48GB RAM, 24 CPUs (high performance)
        """
        range_id = self.range_id

        # Get resource allocations based on profile
        dc_ram, dc_cpus = self.get_resources("dc")
        ws_ram, ws_cpus = self.get_resources("workstation")
        srv_ram, srv_cpus = self.get_resources("server")
        kali_ram, kali_cpus = self.get_resources("kali")

        # Domain Controller (Windows Server 2022)
        # Add AD content and vulnerability roles for realistic AD environment
        from .ad_config import get_realistic_ad_users, get_ad_cs_config, convert_custom_users_to_dict
        
        # Prepare AD role variables - use custom users if provided
        custom_users_dict = None
        if self.customization and self.customization.custom_users:
            custom_users_dict = convert_custom_users_to_dict(self.customization.custom_users)
        
        ad_users = get_realistic_ad_users(custom_users=custom_users_dict)
        
        # Base OUs that are always created
        ad_ous = [
            {"name": "Workstations", "path": "DC=corp,DC=local", "description": "Organizational unit for all workstations"},
            {"name": "Servers", "path": "DC=corp,DC=local", "description": "Organizational unit for all servers"},
        ]
        
        # Base groups that are always created
        ad_groups = [
            {"name": "Domain Users", "scope": "global", "path": "DC=corp,DC=local", "description": "All domain users"},
            {"name": "Domain Admins", "scope": "global", "path": "DC=corp,DC=local", "description": "Domain administrators"},
        ]
        
        # Built-in groups that might be assigned to users
        # These groups already exist in AD (CN=Builtin,DC=corp,DC=local) and should NOT be created
        builtin_group_names = {
            "Power Users", "Backup Operators", "Remote Desktop Users",
            "IIS_IUSRS", "Users", "Administrators", "Guests",
            "Print Operators", "Server Operators", "Account Operators",
        }
        
        # Dynamically create OUs and groups based on departments in the user list
        departments_found = set()
        groups_needed = set()
        
        for user in ad_users:
            dept = user.get("department")
            if dept:
                departments_found.add(dept)
            # Collect all groups that users need
            user_groups = user.get("groups", [])
            for group in user_groups:
                if group not in ["Domain Users", "Domain Admins"]:  # Skip base groups
                    groups_needed.add(group)
        
        # Note: Built-in groups are NOT added to ad_groups because they already exist in AD
        # Users can still be assigned to them even if they're not in the ad_groups list
        
        # Add OUs for all departments found in users
        for dept in sorted(departments_found):
            ad_ous.append({
                "name": dept,
                "path": "DC=corp,DC=local",
                "description": f"{dept} Department"
            })
            # Add corresponding group for each department
            dept_group_name = f"{dept} Department"
            if not any(g["name"] == dept_group_name for g in ad_groups):
                ad_groups.append({
                    "name": dept_group_name,
                    "scope": "global",
                    "path": f"OU={dept},DC=corp,DC=local",
                    "description": f"{dept} Department members"
                })
        
        # Create every other group the users are assigned to (manager groups,
        # Executive, ...). Without this, groups_needed was collected and then
        # discarded, so user creation failed on the DC with
        # "Failed to find the AD object DNs for groups.set. Invalid identities".
        for group_name in sorted(groups_needed):
            if group_name in builtin_group_names:
                continue  # already exists in CN=Builtin; creating it errors
            if any(g["name"] == group_name for g in ad_groups):
                continue
            group_path = "DC=corp,DC=local"
            if "Managers" in group_name:
                dept = group_name.replace("Managers", "").strip()
                if dept in departments_found:
                    group_path = f"OU={dept},DC=corp,DC=local"
            elif group_name in departments_found:
                group_path = f"OU={group_name},DC=corp,DC=local"
            ad_groups.append({
                "name": group_name,
                "scope": "global",
                "path": group_path,
                "description": f"{group_name} group",
            })

        # If no custom users, ensure default departments are included
        if not custom_users_dict:
            default_departments = ["IT", "HR", "Finance"]
            for dept in default_departments:
                if dept not in departments_found:
                    ad_ous.append({
                        "name": dept,
                        "path": "DC=corp,DC=local",
                        "description": f"{dept} Department"
                    })
                    dept_group_name = f"{dept} Department"
                    if not any(g["name"] == dept_group_name for g in ad_groups):
                        ad_groups.append({
                            "name": dept_group_name,
                            "scope": "global",
                            "path": f"OU={dept},DC=corp,DC=local",
                            "description": f"{dept} Department members"
                        })
        
        # Convert ad_users to format expected by ludus-ad-content role
        ludus_ad_users = []
        for user in ad_users:
            ludus_ad_users.append({
                "name": user["username"],
                "firstname": user.get("display_name", "").split()[0] if user.get("display_name") else "",
                "surname": user.get("display_name", "").split()[-1] if user.get("display_name") else "",
                "display_name": user.get("display_name", user["username"]),
                "password": user["password"],
                "path": f"OU={user['department']},DC=corp,DC=local" if user.get("department") else "DC=corp,DC=local",
                "description": user.get("description", ""),
                "groups": user.get("groups", []),
            })
        
        # Add DC VM with AD roles
        self.add_vm(
            vm_name=f"{range_id}-dc-win2022-server-x64",
            hostname=f"{range_id}-DC01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=10,
            ram_gb=dc_ram,
            cpus=dc_cpus,
            windows={"sysprep": False},
            domain={"fqdn": "corp.local", "role": "primary-dc"},
            ansible_roles=[
                {
                    "name": "ludus-ad-content",
                    "vars": {
                        "ludus_ad": {
                            "ous": ad_ous,
                            "groups": ad_groups,
                            "users": ludus_ad_users,
                        }
                    }
                },
                {
                    "name": "ludus-ad-vulns",
                    "vars": {
                        "ludus_ad_vulns_openshares": True,
                        "unconstrained_delegation_machine": False,
                    }
                }
            ],
        )

        # Employee Workstations - check for VM customization
        workstation_count = 2  # Default
        if self.customization and self.customization.vm_customization:
            vm_custom = self.customization.vm_customization
            if "workstation" in vm_custom.vm_count_overrides:
                workstation_count = vm_custom.vm_count_overrides["workstation"]
        
        for i in range(1, workstation_count + 1):
            self.add_vm(
                vm_name=f"{range_id}-workstation-{i}-win11",
                hostname=f"{range_id}-WS{i:02d}",
                template="win11-22h2-x64-enterprise-template",
                vlan=10,
                ip_last_octet=20 + i,
                ram_gb=ws_ram,
                cpus=ws_cpus,
                windows={
                    "chocolatey_packages": ["googlechrome", "notepadplusplus"],
                    "chocolatey_ignore_checksums": True,
                },
                domain={"fqdn": "corp.local", "role": "member"},
            )

        # File Server
        self.add_vm(
            vm_name=f"{range_id}-fileserver-win2022-server-x64",
            hostname=f"{range_id}-FILES01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=15,
            ram_gb=srv_ram,
            cpus=srv_cpus,
            domain={"fqdn": "corp.local", "role": "member"},
        )

        # Red Team Attacker
        self.add_vm(
            vm_name=f"{range_id}-kali",
            hostname=f"{range_id}-KALI",
            template="kali-x64-desktop-template",
            vlan=99,
            ip_last_octet=10,
            ram_gb=kali_ram,
            cpus=kali_cpus,
            linux=True,
            testing={"snapshot": False, "block_internet": False},
        )

        # Add SIEM server if SIEM type is not "none"
        if self.siem_type != "none":
            self.add_siem_server(vlan=10, ip_last_octet=100, siem_type=self.siem_type)
            # Add SIEM agents to all VMs
            self.add_siem_agents_to_all_vms()

        # Network rules
        self.add_network_rule(
            "Allow attacker to corporate network",
            vlan_src=99,
            vlan_dst=10,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # Allow corporate to attacker (for C2 callbacks)
        for port in [80, 443, 8080, 8443]:
            self.add_network_rule(
                f"Allow corporate to attacker on port {port}",
                vlan_src=10,
                vlan_dst=99,
                protocol="tcp",
                ports=port,
                action="ACCEPT",
            )

        return self

    def build_redteam_lab_intermediate(self) -> "RedTeamScenarioBuilder":
        """Build intermediate red team lab - Medium enterprise with segmentation.

        Realistic scenario: Medium-sized enterprise with network segmentation
        - DMZ with web server (external-facing)
        - Internal network with DC, workstations, and servers
        - Database server (high-value target)
        - File server with sensitive data
        - Multiple workstations simulating different departments

        Attack scenarios:
        - Initial foothold via DMZ compromise
        - Pivoting from DMZ to internal network
        - Kerberoasting attacks
        - Pass-the-hash / Pass-the-ticket
        - Lateral movement across departments
        - Database compromise
        - Domain admin compromise

        Resource requirements: 56GB RAM, 24 CPUs
        """
        range_id = self.range_id

        # DMZ Network (VLAN 20)
        # Web Server (externally accessible)
        self.add_vm(
            vm_name=f"{range_id}-dmz-web-win2022-server-x64",
            hostname=f"{range_id}-WEB01",
            template="win2022-server-x64-template",
            vlan=20,
            ip_last_octet=10,
            ram_gb=4,
            cpus=2,
            windows={"sysprep": False},
        )

        # Internal Corporate Network (VLAN 10)
        # Domain Controller with realistic AD configuration
        from .ad_config import get_realistic_ad_users, convert_custom_users_to_dict
        
        # Prepare AD role variables for ludus-ad-content - use custom users if provided
        custom_users_dict = None
        if self.customization and self.customization.custom_users:
            custom_users_dict = convert_custom_users_to_dict(self.customization.custom_users)
        
        ad_users = get_realistic_ad_users(custom_users=custom_users_dict)
        
        # Base OUs that are always created
        ad_ous = [
            {"name": "Workstations", "path": "DC=corp,DC=local", "description": "Organizational unit for all workstations"},
            {"name": "Servers", "path": "DC=corp,DC=local", "description": "Organizational unit for all servers"},
        ]
        
        # Base groups that are always created
        ad_groups = [
            {"name": "Domain Users", "scope": "global", "path": "DC=corp,DC=local", "description": "All domain users"},
            {"name": "Domain Admins", "scope": "global", "path": "DC=corp,DC=local", "description": "Domain administrators"},
        ]
        
        # Built-in groups that might be assigned to users
        # These groups already exist in AD (CN=Builtin,DC=corp,DC=local) and should NOT be created
        builtin_group_names = {
            "Power Users", "Backup Operators", "Remote Desktop Users",
            "IIS_IUSRS", "Users", "Administrators", "Guests",
            "Print Operators", "Server Operators", "Account Operators",
        }
        
        # Dynamically create OUs and groups based on departments in the user list
        departments_found = set()
        groups_needed = set()
        
        for user in ad_users:
            dept = user.get("department")
            if dept:
                departments_found.add(dept)
            # Collect all groups that users need
            user_groups = user.get("groups", [])
            for group in user_groups:
                if group not in ["Domain Users", "Domain Admins"]:  # Skip base groups
                    groups_needed.add(group)
        
        # Note: Built-in groups are NOT added to ad_groups because they already exist in AD
        # Users can still be assigned to them even if they're not in the ad_groups list
        
        # Add OUs for all departments found in users
        for dept in sorted(departments_found):
            ad_ous.append({
                "name": dept,
                "path": "DC=corp,DC=local",
                "description": f"{dept} Department"
            })
            # Add corresponding group for each department
            dept_group_name = f"{dept} Department"
            if not any(g["name"] == dept_group_name for g in ad_groups):
                ad_groups.append({
                    "name": dept_group_name,
                    "scope": "global",
                    "path": f"OU={dept},DC=corp,DC=local",
                    "description": f"{dept} Department members"
                })
        
        # Create every other group the users are assigned to (manager groups,
        # Executive, ...). Without this, groups_needed was collected and then
        # discarded, so user creation failed on the DC with
        # "Failed to find the AD object DNs for groups.set. Invalid identities".
        for group_name in sorted(groups_needed):
            if group_name in builtin_group_names:
                continue  # already exists in CN=Builtin; creating it errors
            if any(g["name"] == group_name for g in ad_groups):
                continue
            group_path = "DC=corp,DC=local"
            if "Managers" in group_name:
                dept = group_name.replace("Managers", "").strip()
                if dept in departments_found:
                    group_path = f"OU={dept},DC=corp,DC=local"
            elif group_name in departments_found:
                group_path = f"OU={group_name},DC=corp,DC=local"
            ad_groups.append({
                "name": group_name,
                "scope": "global",
                "path": group_path,
                "description": f"{group_name} group",
            })

        # If no custom users, ensure default departments are included
        if not custom_users_dict:
            default_departments = ["IT", "HR", "Finance", "Sales"]
            for dept in default_departments:
                if dept not in departments_found:
                    ad_ous.append({
                        "name": dept,
                        "path": "DC=corp,DC=local",
                        "description": f"{dept} Department"
                    })
                    dept_group_name = f"{dept} Department"
                    if not any(g["name"] == dept_group_name for g in ad_groups):
                        ad_groups.append({
                            "name": dept_group_name,
                            "scope": "global",
                            "path": f"OU={dept},DC=corp,DC=local",
                            "description": f"{dept} Department members"
                        })
        
        # Convert ad_users to format expected by ludus-ad-content role
        ludus_ad_users = []
        for user in ad_users:
            ludus_ad_users.append({
                "name": user["username"],
                "firstname": user.get("display_name", "").split()[0] if user.get("display_name") else "",
                "surname": user.get("display_name", "").split()[-1] if user.get("display_name") else "",
                "display_name": user.get("display_name", user["username"]),
                "password": user["password"],
                "path": f"OU={user['department']},DC=corp,DC=local" if user.get("department") else "DC=corp,DC=local",
                "description": user.get("description", ""),
                "groups": user.get("groups", []),
            })
        
        dc_ram, dc_cpus = self.get_resources("dc")
        self.add_vm(
            vm_name=f"{range_id}-dc-win2022-server-x64",
            hostname=f"{range_id}-DC01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=10,
            ram_gb=dc_ram,
            cpus=dc_cpus,
            windows={"sysprep": False},
            domain={"fqdn": "corp.local", "role": "primary-dc"},
            ansible_roles=[
                {
                    "name": "ludus-ad-content",
                    "vars": {
                        "ludus_ad": {
                            "ous": ad_ous,
                            "groups": ad_groups,
                            "users": ludus_ad_users,
                        }
                    }
                },
                {
                    "name": "ludus-ad-vulns",
                    "vars": {
                        # Pass all vulnerability flags if customization is provided
                        **(
                            {
                                "ludus_ad_vulns_openshares": self.customization.vulnerability_config.open_shares,
                                "unconstrained_delegation_machine": self.customization.vulnerability_config.unconstrained_delegation,
                                "asrep_roasting_enabled": self.customization.vulnerability_config.asrep_roasting_enabled,
                                "kerberoastable_accounts": self.customization.vulnerability_config.kerberoastable_accounts,
                                "constrained_delegation": self.customization.vulnerability_config.constrained_delegation,
                                "resource_based_constrained_delegation": self.customization.vulnerability_config.resource_based_constrained_delegation,
                                "dcsync_abuse": self.customization.vulnerability_config.dcsync_abuse,
                                "gpp_passwords": self.customization.vulnerability_config.gpp_passwords,
                                "smb_signing_disabled": self.customization.vulnerability_config.smb_signing_disabled,
                                "llmnr_enabled": self.customization.vulnerability_config.llmnr_enabled,
                                "nbns_enabled": self.customization.vulnerability_config.nbns_enabled,
                                "ms_efsrpc_abuse": self.customization.vulnerability_config.ms_efsrpc_abuse,
                                "print_spooler_enabled": self.customization.vulnerability_config.print_spooler_enabled,
                                "wmi_abuse": self.customization.vulnerability_config.wmi_abuse,
                                "scheduled_tasks_weak_permissions": self.customization.vulnerability_config.scheduled_tasks_weak_permissions,
                                "service_weak_permissions": self.customization.vulnerability_config.service_weak_permissions,
                                "unquoted_service_paths": self.customization.vulnerability_config.unquoted_service_paths,
                                "writable_shares": self.customization.vulnerability_config.writable_shares,
                                "rdp_enabled": self.customization.vulnerability_config.rdp_enabled,
                                "rdp_weak_credentials": self.customization.vulnerability_config.rdp_weak_credentials,
                                "dns_admins_abuse": self.customization.vulnerability_config.dns_admins_abuse,
                                "backup_operators_abuse": self.customization.vulnerability_config.backup_operators_abuse,
                                "seimpersonate_privilege_abuse": self.customization.vulnerability_config.seimpersonate_privilege_abuse,
                                "sebackup_privilege_abuse": self.customization.vulnerability_config.sebackup_privilege_abuse,
                            }
                            if self.customization and self.customization.vulnerability_config
                            else {}
                        ),
                        # Default values if no customization
                        **(
                            {
                                "ludus_ad_vulns_openshares": True,
                                "unconstrained_delegation_machine": False,
                            }
                            if not (self.customization and self.customization.vulnerability_config)
                            else {}
                        ),
                    }
                }
            ],
        )
        
        # AD CS (Certificate Services) Server for certificate-based attacks
        self.add_vm(
            vm_name=f"{range_id}-adcs-win2022-server-x64",
            hostname=f"{range_id}-ADCS01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=12,
            ram_gb=4,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "badsectorlabs.ludus_adcs",  # Correct Ludus role from docs
                    "vars": {
                        "ad_cs_config": get_ad_cs_config(
                            vulnerability_config=(
                                {
                                    "esc1_enabled": self.customization.vulnerability_config.esc1_enabled,
                                    "esc2_enabled": self.customization.vulnerability_config.esc2_enabled,
                                    "esc3_enabled": self.customization.vulnerability_config.esc3_enabled,
                                    "esc4_enabled": self.customization.vulnerability_config.esc4_enabled,
                                    "esc6_enabled": self.customization.vulnerability_config.esc6_enabled,
                                    "esc7_enabled": self.customization.vulnerability_config.esc7_enabled,
                                    "esc8_enabled": self.customization.vulnerability_config.esc8_enabled,
                                }
                                if self.customization and self.customization.vulnerability_config
                                else None
                            )
                        ),
                        "ca_name": "CORP-CA",
                        "ca_type": "Enterprise Root CA",
                    },
                },
            ],
        )

        # File Server
        self.add_vm(
            vm_name=f"{range_id}-fileserver-win2022-server-x64",
            hostname=f"{range_id}-FILES01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=15,
            ram_gb=6,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
        )

        # Database Server (SQL Server) with service account
        sql_ram, sql_cpus = self.get_resources("sql_server")
        self.add_vm(
            vm_name=f"{range_id}-sql-win2022-server-x64",
            hostname=f"{range_id}-SQL01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=25,
            ram_gb=sql_ram,
            cpus=sql_cpus,
            domain={"fqdn": "corp.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "badsectorlabs.ludus_mssql",  # Correct Ludus role from docs
                    "vars": {
                        # See https://docs.ludus.cloud/docs/roles/ for available vars
                        # sql_service_account and other vars may need to be adjusted per role requirements
                    },
                },
            ],
        )

        # Workstations (different departments)
        departments = ["HR", "IT", "FINANCE", "SALES"]
        for i, dept in enumerate(departments, start=1):
            self.add_vm(
                vm_name=f"{range_id}-{dept.lower()}-ws-win11",
                hostname=f"{range_id}-{dept}-WS01",
                template="win11-22h2-x64-enterprise-template",
                vlan=10,
                ip_last_octet=30 + i,
                ram_gb=4,
                cpus=2,
                windows={
                    "chocolatey_packages": ["googlechrome", "notepadplusplus", "7zip"],
                    "chocolatey_ignore_checksums": True,
                },
                domain={"fqdn": "corp.local", "role": "member"},
            )

        # Red Team Attacker (external network)
        self.add_vm(
            vm_name=f"{range_id}-kali",
            hostname=f"{range_id}-KALI",
            template="kali-x64-desktop-template",
            vlan=99,
            ip_last_octet=10,
            ram_gb=8,
            cpus=4,
            linux=True,
            testing={"snapshot": False, "block_internet": False},
        )

        # Network Rules
        # Attacker can reach DMZ (simulating internet-facing access)
        self.add_network_rule(
            "Allow attacker to DMZ",
            vlan_src=99,
            vlan_dst=20,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # DMZ can reach internal (for web app to backend communication)
        self.add_network_rule(
            "Allow DMZ to internal network",
            vlan_src=20,
            vlan_dst=10,
            protocol="tcp",
            ports="all",  # Use "all" for multiple ports to avoid validation issues
            action="ACCEPT",
        )

        # Internal can reach DMZ
        self.add_network_rule(
            "Allow internal to DMZ",
            vlan_src=10,
            vlan_dst=20,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # C2 callback routes
        for port in [80, 443, 8080, 8443, 4444]:
            self.add_network_rule(
                f"Allow internal to attacker C2 on port {port}",
                vlan_src=10,
                vlan_dst=99,
                protocol="tcp",
                ports=port,
                action="ACCEPT",
            )
            self.add_network_rule(
                f"Allow DMZ to attacker C2 on port {port}",
                vlan_src=20,
                vlan_dst=99,
                protocol="tcp",
                ports=port,
                action="ACCEPT",
            )

        # Add Wazuh SIEM with OPSEC detection rules (intermediate/advanced only)
        if self.siem_type == "wazuh":
            siem_ram, siem_cpus = self.get_resources("siem")
            self.add_siem_server(vlan=10, ip_last_octet=100, siem_type="wazuh")
            # Enhance Wazuh with OPSEC detection rules - find and update the Wazuh VM config
            for vm in self.config["ludus"]:
                if "wazuh" in vm.get("vm_name", "").lower() and "server" in vm.get("vm_name", "").lower():
                    if "ansible_roles" not in vm:
                        vm["ansible_roles"] = []
                    vm["ansible_roles"].append({
                        "name": "ludus.wazuh_opsec",
                        "vars": get_wazuh_opsec_ansible_vars(),
                    })
                    break
            # Add SIEM agents to all VMs
            self.add_siem_agents_to_all_vms()

        return self

    def build_redteam_lab_advanced(self) -> "RedTeamScenarioBuilder":
        """Build advanced red team lab - Large enterprise with TWO FORESTS requiring forest pivoting.

        Realistic scenario: Large enterprise with multi-forest environment
        - Forest 1: CORP.LOCAL (Primary corporate forest)
        - Forest 2: PARTNER.LOCAL (Partner/acquisition forest)
        - Forest trust relationship between forests
        - Multi-tier network architecture (DMZ, Internal, Secure)
        - Multiple servers (Web, DB, File, Exchange, Backup)
        - Workstations across multiple departments
        - Jump server for administrative access
        - Sensitive data on secure network

        Attack scenarios requiring forest pivoting:
        - Initial compromise in Forest 1 (CORP.LOCAL)
        - Enumerate forest trust relationships
        - Pivot to Forest 2 (PARTNER.LOCAL) via trust
        - Cross-forest Kerberoasting
        - Cross-forest Golden Ticket attacks
        - Cross-forest DCSync
        - Trust relationship exploitation
        - Multi-stage attack chain from DMZ to secure zone
        - Golden/Silver ticket attacks
        - Kerberoasting and AS-REP roasting
        - Constrained/Unconstrained delegation abuse
        - NTLM relay attacks
        - Privilege escalation via vulnerable services
        - Data exfiltration from secure zone
        - Persistence mechanisms
        - Living-off-the-land techniques

        Resource requirements: 120GB RAM, 50 CPUs
        """
        range_id = self.range_id

        # DMZ Network (VLAN 30) - Internet-facing
        # External Web Server
        self.add_vm(
            vm_name=f"{range_id}-dmz-web-win2022-server-x64",
            hostname=f"{range_id}-WEB01",
            template="win2022-server-x64-template",
            vlan=30,
            ip_last_octet=10,
            ram_gb=4,
            cpus=2,
            windows={"sysprep": False},
        )

        # Reverse Proxy / Load Balancer
        self.add_vm(
            vm_name=f"{range_id}-dmz-proxy-ubuntu22",
            hostname=f"{range_id}-PROXY01",
            template="ubuntu-22.04-x64-server-template",
            vlan=30,
            ip_last_octet=11,
            ram_gb=4,
            cpus=2,
            linux=True,
        )

        # Internal Corporate Network (VLAN 10) - Parent Domain
        # Parent Domain Controller with realistic AD configuration
        from .ad_config import get_realistic_ad_users, convert_custom_users_to_dict
        
        # Prepare AD role variables for ludus-ad-content (corp.local forest)
        # Use custom users if provided
        custom_users_dict = None
        if self.customization and self.customization.custom_users:
            custom_users_dict = convert_custom_users_to_dict(self.customization.custom_users)
        
        ad_users_corp = get_realistic_ad_users(custom_users=custom_users_dict)
        ad_ous_corp = [
            {"name": "Workstations", "path": "DC=corp,DC=local", "description": "Organizational unit for all workstations"},
            {"name": "Servers", "path": "DC=corp,DC=local", "description": "Organizational unit for all servers"},
            {"name": "IT", "path": "DC=corp,DC=local", "description": "IT Department"},
            {"name": "HR", "path": "DC=corp,DC=local", "description": "Human Resources Department"},
            {"name": "Finance", "path": "DC=corp,DC=local", "description": "Finance Department"},
            {"name": "Sales", "path": "DC=corp,DC=local", "description": "Sales Department"},
            {"name": "Executive", "path": "DC=corp,DC=local", "description": "Executive Leadership"},
        ]
        
        ad_groups_corp = [
            {"name": "Domain Users", "scope": "global", "path": "DC=corp,DC=local", "description": "All domain users"},
            {"name": "Domain Admins", "scope": "global", "path": "DC=corp,DC=local", "description": "Domain administrators"},
            {"name": "IT Department", "scope": "global", "path": "OU=IT,DC=corp,DC=local", "description": "IT Department members"},
            {"name": "HR Department", "scope": "global", "path": "OU=HR,DC=corp,DC=local", "description": "HR Department members"},
            {"name": "Finance Department", "scope": "global", "path": "OU=Finance,DC=corp,DC=local", "description": "Finance Department members"},
        ]
        
        ludus_ad_users_corp = []
        for user in ad_users_corp:
            ludus_ad_users_corp.append({
                "name": user["username"],
                "firstname": user.get("display_name", "").split()[0] if user.get("display_name") else "",
                "surname": user.get("display_name", "").split()[-1] if user.get("display_name") else "",
                "display_name": user.get("display_name", user["username"]),
                "password": user["password"],
                "path": f"OU={user['department']},DC=corp,DC=local" if user.get("department") else "DC=corp,DC=local",
                "description": user.get("description", ""),
                "groups": user.get("groups", []),
            })
        
        dc_ram, dc_cpus = self.get_resources("dc")
        self.add_vm(
            vm_name=f"{range_id}-parent-dc-win2022-server-x64",
            hostname=f"{range_id}-PARENT-DC01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=10,
            ram_gb=dc_ram,
            cpus=dc_cpus,
            windows={"sysprep": False},
            domain={"fqdn": "corp.local", "role": "primary-dc"},
            ansible_roles=[
                {
                    "name": "ludus-ad-content",
                    "vars": {
                        "ludus_ad": {
                            "ous": ad_ous_corp,
                            "groups": ad_groups_corp,
                            "users": ludus_ad_users_corp,
                        }
                    }
                },
                {
                    "name": "ludus-ad-vulns",
                    "vars": {
                        "ludus_ad_vulns_openshares": True,
                        "unconstrained_delegation_machine": False,
                    }
                }
            ],
        )
        
        # AD CS (Certificate Services) Server for advanced certificate-based attacks
        self.add_vm(
            vm_name=f"{range_id}-adcs-win2022-server-x64",
            hostname=f"{range_id}-ADCS01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=12,
            ram_gb=6,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "badsectorlabs.ludus_adcs",  # Correct Ludus role from docs
                    "vars": {
                        "ad_cs_config": get_ad_cs_config(
                            vulnerability_config=(
                                {
                                    "esc1_enabled": self.customization.vulnerability_config.esc1_enabled,
                                    "esc2_enabled": self.customization.vulnerability_config.esc2_enabled,
                                    "esc3_enabled": self.customization.vulnerability_config.esc3_enabled,
                                    "esc4_enabled": self.customization.vulnerability_config.esc4_enabled,
                                    "esc6_enabled": self.customization.vulnerability_config.esc6_enabled,
                                    "esc7_enabled": self.customization.vulnerability_config.esc7_enabled,
                                    "esc8_enabled": self.customization.vulnerability_config.esc8_enabled,
                                }
                                if self.customization and self.customization.vulnerability_config
                                else None
                            )
                        ),
                        "ca_name": "CORP-CA",
                        "ca_type": "Enterprise Root CA",
                    },
                },
            ],
        )

        # File Server
        self.add_vm(
            vm_name=f"{range_id}-fileserver-win2022-server-x64",
            hostname=f"{range_id}-FILES01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=20,
            ram_gb=6,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
        )

        # SQL Server (high-value target) with service account
        sql_ram, sql_cpus = self.get_resources("sql_server")
        self.add_vm(
            vm_name=f"{range_id}-sql-win2022-server-x64",
            hostname=f"{range_id}-SQL01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=25,
            ram_gb=sql_ram,
            cpus=sql_cpus,
            domain={"fqdn": "corp.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "badsectorlabs.ludus_mssql",  # Correct Ludus role from docs
                    "vars": {
                        # See https://docs.ludus.cloud/docs/roles/ for available vars
                        # sql_service_account and other vars may need to be adjusted per role requirements
                    },
                },
            ],
        )

        # Exchange Server with service account
        exch_ram, exch_cpus = self.get_resources("exchange_server")
        self.add_vm(
            vm_name=f"{range_id}-exchange-win2022-server-x64",
            hostname=f"{range_id}-EXCH01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=30,
            ram_gb=exch_ram,
            cpus=exch_cpus,
            domain={"fqdn": "corp.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "aleemladha.ludus_exchange",  # Correct Ludus role from docs
                    "vars": {
                        "exchange_service_account": "svc_exchange",
                        "exchange_install": True,
                    },
                },
            ],
        )

        # Jump/Admin Server
        self.add_vm(
            vm_name=f"{range_id}-jumpbox-win2022-server-x64",
            hostname=f"{range_id}-JUMP01",
            template="win2022-server-x64-template",
            vlan=10,
            ip_last_octet=35,
            ram_gb=4,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
        )

        # Workstations in parent domain
        departments = ["IT", "HR", "FINANCE"]
        for i, dept in enumerate(departments, start=1):
            self.add_vm(
                vm_name=f"{range_id}-{dept.lower()}-ws-win11",
                hostname=f"{range_id}-{dept}-WS01",
                template="win11-22h2-x64-enterprise-template",
                vlan=10,
                ip_last_octet=40 + i,
                ram_gb=4,
                cpus=2,
                windows={
                    "chocolatey_packages": ["googlechrome", "notepadplusplus", "7zip"],
                    "chocolatey_ignore_checksums": True,
                },
                domain={"fqdn": "corp.local", "role": "member"},
            )

        # Forest 2: PARTNER.LOCAL (VLAN 20) - Partner/Acquisition Forest
        # This is a SEPARATE FOREST (not a child domain) requiring forest trust pivoting
        # Partner Forest Root Domain Controller
        # Prepare AD role variables for ludus-ad-content (partner.local forest)
        ad_ous_partner = [
            {"name": "Workstations", "path": "DC=partner,DC=local", "description": "Organizational unit for all workstations"},
            {"name": "Servers", "path": "DC=partner,DC=local", "description": "Organizational unit for all servers"},
            {"name": "IT", "path": "DC=partner,DC=local", "description": "IT Department"},
            {"name": "HR", "path": "DC=partner,DC=local", "description": "Human Resources Department"},
            {"name": "Finance", "path": "DC=partner,DC=local", "description": "Finance Department"},
        ]
        
        ad_groups_partner = [
            {"name": "Domain Users", "scope": "global", "path": "DC=partner,DC=local", "description": "All domain users"},
            {"name": "Domain Admins", "scope": "global", "path": "DC=partner,DC=local", "description": "Domain administrators"},
            {"name": "IT Department", "scope": "global", "path": "OU=IT,DC=partner,DC=local", "description": "IT Department members"},
        ]
        
        ludus_ad_users_partner = []
        for user in ad_users_corp:  # Use same users for partner forest
            ludus_ad_users_partner.append({
                "name": user["username"],
                "firstname": user.get("display_name", "").split()[0] if user.get("display_name") else "",
                "surname": user.get("display_name", "").split()[-1] if user.get("display_name") else "",
                "display_name": user.get("display_name", user["username"]),
                "password": user["password"],
                "path": f"OU={user['department']},DC=partner,DC=local" if user.get("department") else "DC=partner,DC=local",
                "description": user.get("description", ""),
                "groups": user.get("groups", []),
            })
        
        dc_ram, dc_cpus = self.get_resources("dc")
        self.add_vm(
            vm_name=f"{range_id}-partner-dc-win2022-server-x64",
            hostname=f"{range_id}-PARTNER-DC01",
            template="win2022-server-x64-template",
            vlan=20,
            ip_last_octet=10,
            ram_gb=dc_ram,
            cpus=dc_cpus,
            windows={"sysprep": False},
            domain={"fqdn": "partner.local", "role": "primary-dc"},
            ansible_roles=[
                {
                    "name": "ludus-ad-content",
                    "vars": {
                        "ludus_ad": {
                            "ous": ad_ous_partner,
                            "groups": ad_groups_partner,
                            "users": ludus_ad_users_partner,
                        }
                    }
                },
                {
                    "name": "ludus-ad-vulns",
                    "vars": {
                        "ludus_ad_vulns_openshares": True,
                        "unconstrained_delegation_machine": False,
                    }
                }
            ],
        )
        
        # Partner Forest AD CS Server
        self.add_vm(
            vm_name=f"{range_id}-partner-adcs-win2022-server-x64",
            hostname=f"{range_id}-PARTNER-ADCS01",
            template="win2022-server-x64-template",
            vlan=20,
            ip_last_octet=12,
            ram_gb=6,
            cpus=2,
            domain={"fqdn": "partner.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "badsectorlabs.ludus_adcs",  # Correct Ludus role from docs
                    "vars": {
                        "ad_cs_config": get_ad_cs_config(
                            vulnerability_config=(
                                {
                                    "esc1_enabled": self.customization.vulnerability_config.esc1_enabled,
                                    "esc2_enabled": self.customization.vulnerability_config.esc2_enabled,
                                    "esc3_enabled": self.customization.vulnerability_config.esc3_enabled,
                                    "esc4_enabled": self.customization.vulnerability_config.esc4_enabled,
                                    "esc6_enabled": self.customization.vulnerability_config.esc6_enabled,
                                    "esc7_enabled": self.customization.vulnerability_config.esc7_enabled,
                                    "esc8_enabled": self.customization.vulnerability_config.esc8_enabled,
                                }
                                if self.customization and self.customization.vulnerability_config
                                else None
                            )
                        ),
                        "ca_name": "PARTNER-CA",
                        "ca_type": "Enterprise Root CA",
                    },
                },
            ],
        )
        
        # Partner Forest File Server (high-value target)
        self.add_vm(
            vm_name=f"{range_id}-partner-fileserver-win2022-server-x64",
            hostname=f"{range_id}-PARTNER-FILES01",
            template="win2022-server-x64-template",
            vlan=20,
            ip_last_octet=20,
            ram_gb=6,
            cpus=2,
            domain={"fqdn": "partner.local", "role": "member"},
        )
        
        # Partner Forest SQL Server
        sql_ram, sql_cpus = self.get_resources("sql_server")
        self.add_vm(
            vm_name=f"{range_id}-partner-sql-win2022-server-x64",
            hostname=f"{range_id}-PARTNER-SQL01",
            template="win2022-server-x64-template",
            vlan=20,
            ip_last_octet=25,
            ram_gb=sql_ram,
            cpus=sql_cpus,
            domain={"fqdn": "partner.local", "role": "member"},
            ansible_roles=[
                {
                    "name": "badsectorlabs.ludus_mssql",  # Correct Ludus role from docs
                    "vars": {
                        # See https://docs.ludus.cloud/docs/roles/ for available vars
                        # sql_service_account and other vars may need to be adjusted per role requirements
                    },
                },
            ],
        )

        # Partner Forest workstations
        for i in range(1, 3):
            self.add_vm(
                vm_name=f"{range_id}-partner-ws{i}-win11",
                hostname=f"{range_id}-PARTNER-WS{i:02d}",
                template="win11-22h2-x64-enterprise-template",
                vlan=20,
                ip_last_octet=30 + i,
                ram_gb=4,
                cpus=2,
                windows={
                    "chocolatey_packages": ["googlechrome", "notepadplusplus"],
                    "chocolatey_ignore_checksums": True,
                },
                domain={"fqdn": "partner.local", "role": "member"},
            )

        # Secure Zone (VLAN 15) - Sensitive data and backups
        # Backup Server
        self.add_vm(
            vm_name=f"{range_id}-backup-win2022-server-x64",
            hostname=f"{range_id}-BACKUP01",
            template="win2022-server-x64-template",
            vlan=15,
            ip_last_octet=10,
            ram_gb=8,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
        )

        # Secure File Server (sensitive data)
        self.add_vm(
            vm_name=f"{range_id}-secure-files-win2022-server-x64",
            hostname=f"{range_id}-SECURE-FILES01",
            template="win2022-server-x64-template",
            vlan=15,
            ip_last_octet=20,
            ram_gb=6,
            cpus=2,
            domain={"fqdn": "corp.local", "role": "member"},
        )

        # Red Team Attacker (external)
        self.add_vm(
            vm_name=f"{range_id}-kali",
            hostname=f"{range_id}-KALI",
            template="kali-x64-desktop-template",
            vlan=99,
            ip_last_octet=10,
            ram_gb=8,
            cpus=4,
            linux=True,
            testing={"snapshot": False, "block_internet": False},
        )

        # Network Rules - Realistic enterprise segmentation
        # Attacker can reach DMZ only
        self.add_network_rule(
            "Allow attacker to DMZ",
            vlan_src=99,
            vlan_dst=30,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # DMZ to Internal (limited ports)
        self.add_network_rule(
            "Allow DMZ to internal on specific ports",
            vlan_src=30,
            vlan_dst=10,
            protocol="tcp",
            ports="all",  # Use "all" for multiple ports to avoid validation issues
            action="ACCEPT",
        )

        # Internal to DMZ (monitoring/management)
        self.add_network_rule(
            "Allow internal to DMZ",
            vlan_src=10,
            vlan_dst=30,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # Forest 1 (CORP.LOCAL) to Forest 2 (PARTNER.LOCAL) - Forest Trust Communication
        # Required for forest trust authentication and replication
        self.add_network_rule(
            "Allow Forest 1 to Forest 2 (forest trust)",
            vlan_src=10,
            vlan_dst=20,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # Forest 2 (PARTNER.LOCAL) to Forest 1 (CORP.LOCAL) - Forest Trust Communication
        self.add_network_rule(
            "Allow Forest 2 to Forest 1 (forest trust)",
            vlan_src=20,
            vlan_dst=10,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )
        
        # Forest trust requires specific ports for authentication
        for port in [88, 389, 445, 636, 3268, 3269]:  # Kerberos, LDAP, SMB, LDAPS, GC, GC-SSL
            self.add_network_rule(
                f"Allow Forest 1 to Forest 2 DC on port {port} (forest trust)",
                vlan_src=10,
                vlan_dst=20,
                protocol="tcp",
                ports=port,
                action="ACCEPT",
            )
            self.add_network_rule(
                f"Allow Forest 2 to Forest 1 DC on port {port} (forest trust)",
                vlan_src=20,
                vlan_dst=10,
                protocol="tcp",
                ports=port,
                action="ACCEPT",
            )

        # Internal to Secure Zone (restricted)
        self.add_network_rule(
            "Allow internal to secure zone on specific ports",
            vlan_src=10,
            vlan_dst=15,
            protocol="tcp",
            ports="all",  # Use "all" for multiple ports
            action="ACCEPT",
        )

        # Secure Zone to Internal
        self.add_network_rule(
            "Allow secure zone to internal",
            vlan_src=15,
            vlan_dst=10,
            protocol="all",
            ports="all",
            action="ACCEPT",
        )

        # C2 callback routes (all networks can reach attacker)
        for vlan in [10, 20, 15, 30]:
            for port in [80, 443, 8080, 8443, 4444, 53]:
                self.add_network_rule(
                    f"Allow VLAN {vlan} to attacker C2 on port {port}",
                    vlan_src=vlan,
                    vlan_dst=99,
                    protocol="tcp",
                    ports=port,
                    action="ACCEPT",
                )
        
        # Add forest trust configuration to Forest 1 DC
        for vm in self.config["ludus"]:
            if "parent-dc" in vm.get("vm_name", "").lower() or "PARENT-DC01" in vm.get("hostname", ""):
                if "ansible_roles" not in vm:
                    vm["ansible_roles"] = []
                vm["ansible_roles"].append({
                    "name": "ludus.forest_trust",
                    "vars": {
                        "trust_type": "forest",
                        "trust_direction": "bidirectional",
                        "trust_partner": "partner.local",
                        "trust_password": "TrustPassword123!",
                    },
                })
                break

        # Add Wazuh SIEM with OPSEC detection rules (advanced scenario)
        if self.siem_type == "wazuh":
            siem_ram, siem_cpus = self.get_resources("siem")
            self.add_siem_server(vlan=10, ip_last_octet=100, siem_type="wazuh")
            # Enhance Wazuh with OPSEC detection rules - find and update the Wazuh VM config
            for vm in self.config["ludus"]:
                if "wazuh" in vm.get("vm_name", "").lower() and "server" in vm.get("vm_name", "").lower():
                    if "ansible_roles" not in vm:
                        vm["ansible_roles"] = []
                    vm["ansible_roles"].append({
                        "name": "ludus.wazuh_opsec",
                        "vars": get_wazuh_opsec_ansible_vars(),
                    })
                    break
            # Add SIEM agents to all VMs
            self.add_siem_agents_to_all_vms()

        return self

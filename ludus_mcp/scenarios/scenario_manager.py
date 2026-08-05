"""Manager for deploying security training scenarios."""

import asyncio
import os
from typing import Any

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.scenarios.red_team_scenarios import RedTeamScenarioBuilder
from ludus_mcp.scenarios.blue_team_scenarios import BlueTeamScenarioBuilder
from ludus_mcp.scenarios.purple_team_scenarios import PurpleTeamScenarioBuilder
from ludus_mcp.scenarios.malware_re_scenarios import MalwareREScenarioBuilder
from ludus_mcp.scenarios.wireless_scenarios import WirelessScenarioBuilder
from ludus_mcp.scenarios.ad_scenarios import ADScenarioBuilder
from ludus_mcp.scenarios.role_manager import RoleManager
from ludus_mcp.utils.logging import get_logger
from ..schemas.scenario_customization import (
    ScenarioCustomization,
    ADUserCustomization,
    VulnerabilityConfig,
    NetworkCustomization,
    VMCustomization,
    RandomizationConfig,
)
from .randomizer import randomize_scenario
from .ad_config import convert_custom_users_to_dict
from .walkthrough_generator import generate_scenario_walkthrough

logger = get_logger(__name__)


class ScenarioManager:
    """Manages deployment of security training scenarios."""

    # Scenario metadata: (name, builder_class, builder_method, description, vm_summary)
    # vm_summary helps LLMs understand what will be deployed
    # IMPORTANT: Store builder class and method name (NOT instances) to avoid state reuse
    
    # Range name mapping: scenario_key -> range_name
    # These names will be used when deploying scenarios
    RANGE_NAMES = {
        "redteam-lab-lite": "redteamlite",
        "redteam-lab-intermediate": "redteamint",  # Shorter to avoid Windows hostname truncation
        "redteam-lab-advanced": "redteam-advanced",
        "blueteam-lab-lite": "blueteam",
        "blueteam-lab-intermediate": "blueteamint",
        "blueteam-lab-advanced": "blueteamadv",
        "purpleteam-lab-lite": "purpleteamlite",
        "purpleteam-lab-intermediate": "purpleteam-intermediate",
        "purpleteam-lab-advanced": "purpleteam-advanced",
        "malware-re-lab-lite": "malware-re-lite",
        "malware-re-lab-intermediate": "malware-re-intermediate",
        "malware-re-lab-advanced": "malware-re-advanced",
        "wireless-lab": "wireless-lab",
        "ad-basic": "ad-basic",
        "ad-fileserver": "ad-fileserver",
        "ad-sql": "ad-sql",
        "ad-forest": "ad-forest",
    }
    
    SCENARIOS = {
        # Red Team Scenarios
        "redteam-lab-lite": (
            "Red Team Lab - Lite",
            RedTeamScenarioBuilder,
            "build_redteam_lab_lite",
            "Small business environment for red team operations - basic AD with file server",
            "4 VMs | Minimal: 14GB RAM, 12 CPUs | Recommended: 24GB, 12 CPUs | Max: 48GB, 24 CPUs"
        ),
        "redteam-lab-intermediate": (
            "Red Team Lab - Intermediate",
            RedTeamScenarioBuilder,
            "build_redteam_lab_intermediate",
            "Medium enterprise with DMZ and internal network segmentation",
            "9 VMs | Minimal: 24GB RAM, 20 CPUs | Recommended: 48GB, 28 CPUs | Max: 96GB, 56 CPUs"
        ),
        "redteam-lab-advanced": (
            "Red Team Lab - Advanced",
            RedTeamScenarioBuilder,
            "build_redteam_lab_advanced",
            "Large enterprise with TWO FORESTS (CORP.LOCAL and PARTNER.LOCAL), forest trust, DMZ, internal, and secure zones. Includes realistic AD users, service accounts, AD CS, and Wazuh OPSEC detection.",
            "21 VMs | Minimal: 60GB RAM, 45 CPUs | Recommended: 120GB, 60 CPUs | Max: 240GB, 120 CPUs"
        ),

        # Blue Team Scenarios
        "blueteam-lab-lite": (
            "Blue Team Lab - Lite",
            BlueTeamScenarioBuilder,
            "build_blueteam_lab_lite",
            "Small SOC environment with realistic AD users/service accounts, SIEM with OPSEC detection, and low-intensity live action attack simulations",
            "5 VMs | Minimal: 18GB RAM, 12 CPUs | Recommended: 32GB, 14 CPUs | Max: 64GB, 28 CPUs"
        ),
        "blueteam-lab-intermediate": (
            "Blue Team Lab - Intermediate",
            BlueTeamScenarioBuilder,
            "build_blueteam_lab_intermediate",
            "Medium SOC with realistic AD, AD CS, SIEM with OPSEC detection, EDR, IDS, and medium-intensity live action attack simulations",
            "11 VMs | Minimal: 36GB RAM, 26 CPUs | Recommended: 72GB, 36 CPUs | Max: 144GB, 72 CPUs"
        ),
        "blueteam-lab-advanced": (
            "Blue Team Lab - Advanced",
            BlueTeamScenarioBuilder,
            "build_blueteam_lab_advanced",
            "Enterprise SOC with realistic multi-domain AD, full detection stack, and high-intensity live action attack simulations including forest pivoting",
            "21 VMs | Minimal: 72GB RAM, 56 CPUs | Recommended: 144GB, 80 CPUs | Max: 288GB, 160 CPUs"
        ),

        # Purple Team Scenarios
        "purpleteam-lab-lite": (
            "Purple Team Lab - Lite",
            PurpleTeamScenarioBuilder,
            "build_purpleteam_lab_lite",
            "Small collaborative red/blue exercise with basic detection",
            "6 VMs | Minimal: 24GB RAM, 16 CPUs | Recommended: 48GB, 24 CPUs | Max: 96GB, 48 CPUs"
        ),
        "purpleteam-lab-intermediate": (
            "Purple Team Lab - Intermediate",
            PurpleTeamScenarioBuilder,
            "build_purpleteam_lab_intermediate",
            "Medium purple team engagement with EDR and advanced detection",
            "10 VMs | Minimal: 40GB RAM, 28 CPUs | Recommended: 80GB, 40 CPUs | Max: 160GB, 80 CPUs"
        ),
        "purpleteam-lab-advanced": (
            "Purple Team Lab - Advanced",
            PurpleTeamScenarioBuilder,
            "build_purpleteam_lab_advanced",
            "Enterprise purple team with full SOC stack and adversary emulation",
            "13 VMs | Minimal: 52GB RAM, 36 CPUs | Recommended: 104GB, 52 CPUs | Max: 208GB, 104 CPUs"
        ),

        # Malware Analysis & Reverse Engineering Scenarios
        "malware-re-lab-lite": (
            "Malware Analysis Lab - Lite",
            MalwareREScenarioBuilder,
            "build_malware_re_lab_lite",
            "Basic malware analysis environment with Windows/Linux analysis workstations",
            "3 VMs | Minimal: 10GB RAM, 6 CPUs | Recommended: 20GB, 10 CPUs | Max: 40GB, 20 CPUs"
        ),
        "malware-re-lab-intermediate": (
            "Malware Analysis Lab - Intermediate",
            MalwareREScenarioBuilder,
            "build_malware_re_lab_intermediate",
            "Professional malware lab with sandbox automation and multiple OS targets",
            "7 VMs | Minimal: 28GB RAM, 20 CPUs | Recommended: 56GB, 28 CPUs | Max: 112GB, 56 CPUs"
        ),
        "malware-re-lab-advanced": (
            "Malware Analysis Lab - Advanced",
            MalwareREScenarioBuilder,
            "build_malware_re_lab_advanced",
            "Enterprise malware research facility with automated analysis and threat intel",
            "18 VMs | Minimal: 66GB RAM, 48 CPUs | Recommended: 132GB, 68 CPUs | Max: 264GB, 136 CPUs"
        ),

        # Wireless Security Scenarios
        "wireless-lab": (
            "Wireless Security Lab",
            WirelessScenarioBuilder,
            "build_wireless_lab",
            "Comprehensive WiFi pentesting lab with WiFiChallengeLab Docker environment",
            "2 VMs | Minimal: 8GB RAM, 6 CPUs | Recommended: 16GB, 8 CPUs | Max: 32GB, 16 CPUs"
        ),

        # Active Directory Scenarios
        "ad-basic": (
            "Active Directory Lab - Basic",
            ADScenarioBuilder,
            "build_basic_ad_lab",
            "Basic AD lab with domain controller, workstations, and Kali attacker",
            "4 VMs | Minimal: 24GB RAM, 16 CPUs | Recommended: 32GB, 16 CPUs | Max: 64GB, 32 CPUs"
        ),
        "ad-fileserver": (
            "Active Directory Lab - File Server",
            ADScenarioBuilder,
            "build_ad_with_file_server",
            "AD lab with file server for lateral movement practice",
            "5 VMs | Minimal: 32GB RAM, 20 CPUs | Recommended: 40GB, 20 CPUs | Max: 80GB, 40 CPUs"
        ),
        "ad-sql": (
            "Active Directory Lab - SQL Server",
            ADScenarioBuilder,
            "build_ad_with_sql_server",
            "AD lab with SQL Server for credential theft scenarios",
            "5 VMs | Minimal: 40GB RAM, 20 CPUs | Recommended: 48GB, 20 CPUs | Max: 96GB, 40 CPUs"
        ),
        "ad-forest": (
            "Active Directory Lab - Multi-Domain Forest",
            ADScenarioBuilder,
            "build_ad_forest",
            "Multi-domain AD forest for cross-domain attacks",
            "7 VMs | Minimal: 48GB RAM, 28 CPUs | Recommended: 56GB, 28 CPUs | Max: 112GB, 56 CPUs"
        ),
    }

    def __init__(self, client: LudusAPIClient):
        """Initialize the scenario manager."""
        self.client = client
        # Initialize RoleManager with SSH configuration from environment variables
        self.role_manager = RoleManager(
            client,
            ssh_host=os.getenv("LUDUS_SSH_HOST"),
            ssh_user=os.getenv("LUDUS_SSH_USER"),
            ssh_key_path=os.getenv("LUDUS_SSH_KEY_PATH"),
            ssh_password=os.getenv("LUDUS_SSH_PASSWORD"),
            allow_ssh_install=os.getenv("LUDUS_ALLOW_SSH_INSTALL", "false").lower() == "true",
        )

    async def list_scenarios(self) -> dict[str, str]:
        """List all available scenarios with VM summaries."""
        return {
            key: f"{name} - {vm_summary}"
            for key, (name, _, _, _, vm_summary) in self.SCENARIOS.items()
        }

    async def deploy_scenario(
        self,
        scenario_key: str,
        user_id: str | None = None,
        ensure_roles: bool = True,
        siem_type: str = "wazuh",
        resource_profile: str = "minimal",
        customize: bool = False,
        randomize: bool = False,
        custom_users: list[dict[str, Any]] | None = None,
        vulnerability_config: dict[str, Any] | None = None,
        network_customizations: dict[str, Any] | None = None,
        vm_customizations: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deploy a scenario.

        Args:
            scenario_key: Key identifying the scenario to deploy
            user_id: Optional user ID for deployment
            ensure_roles: Whether to ensure required roles are installed
            siem_type: SIEM type (wazuh, splunk, elastic, security-onion, none)
            resource_profile: Resource allocation profile (minimal, recommended, maximum)
            customize: Enable customization mode (use provided customizations)
            randomize: Enable randomization mode (generate random customizations)
            custom_users: List of custom user dictionaries (username, password, groups, etc.)
            vulnerability_config: Custom vulnerability configuration dict
            network_customizations: Network customization dict (VLAN changes, firewall rules)
            vm_customizations: VM customization dict (count overrides, resource changes)
        """
        if scenario_key not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_key}")

        # Validate SIEM type
        valid_siem_types = ["wazuh", "splunk", "elastic", "security-onion", "none"]
        if siem_type not in valid_siem_types:
            raise ValueError(f"Invalid SIEM type: {siem_type}. Must be one of: {valid_siem_types}")

        # Validate resource profile
        valid_profiles = ["minimal", "recommended", "maximum"]
        if resource_profile not in valid_profiles:
            raise ValueError(f"Invalid resource profile: {resource_profile}. Must be one of: {valid_profiles}")
        
        name, builder_class, builder_method_name, description, vm_summary = self.SCENARIOS[scenario_key]
        logger.info(f"Building scenario: {name} ({vm_summary}) with SIEM: {siem_type}, Resource Profile: {resource_profile}")
        
        # Handle customization and randomization
        customization: ScenarioCustomization | None = None
        is_customized = False
        is_randomized = False
        
        if randomize:
            logger.info("Randomization enabled - generating random customizations")
            randomization_config = RandomizationConfig()
            customization = randomize_scenario(scenario_key, randomization_config)
            is_randomized = True
            logger.info(f"Generated random customizations: {len(customization.custom_users) if customization.custom_users else 0} users")
        elif customize:
            logger.info("Customization enabled - applying provided customizations")
            customization = ScenarioCustomization()
            is_customized = True
            
            # Convert custom users from dict to ADUserCustomization objects
            if custom_users:
                customization.custom_users = [
                    ADUserCustomization(
                        username=u.get("username", ""),
                        display_name=u.get("display_name", u.get("username", "")),
                        password=u.get("password", ""),
                        department=u.get("department"),
                        title=u.get("title"),
                        groups=u.get("groups", []),
                        password_never_expires=u.get("password_never_expires", False),
                        account_disabled=u.get("account_disabled", False),
                        description=u.get("description"),
                        path=u.get("path"),
                    )
                    for u in custom_users
                ]
                logger.info(f"Using {len(customization.custom_users)} custom users")
            
            # Set vulnerability config
            if vulnerability_config:
                customization.vulnerability_config = VulnerabilityConfig(
                    esc1_enabled=vulnerability_config.get("esc1_enabled"),
                    esc2_enabled=vulnerability_config.get("esc2_enabled"),
                    esc3_enabled=vulnerability_config.get("esc3_enabled"),
                    esc4_enabled=vulnerability_config.get("esc4_enabled"),
                    esc6_enabled=vulnerability_config.get("esc6_enabled"),
                    esc7_enabled=vulnerability_config.get("esc7_enabled"),
                    esc8_enabled=vulnerability_config.get("esc8_enabled"),
                    open_shares=vulnerability_config.get("open_shares"),
                    unconstrained_delegation=vulnerability_config.get("unconstrained_delegation"),
                    kerberoastable_accounts=vulnerability_config.get("kerberoastable_accounts"),
                    custom_config=vulnerability_config.get("custom_config", {}),
                )
                logger.info("Using custom vulnerability configuration")
            
            # Set network customizations
            if network_customizations:
                customization.network_customization = NetworkCustomization(
                    vlan_changes=network_customizations.get("vlan_changes", {}),
                    additional_rules=network_customizations.get("additional_rules", []),
                    remove_rules=network_customizations.get("remove_rules", []),
                    inter_vlan_default=network_customizations.get("inter_vlan_default"),
                )
                logger.info("Using custom network configuration")
            
            # Set VM customizations
            if vm_customizations:
                customization.vm_customization = VMCustomization(
                    vm_count_overrides=vm_customizations.get("vm_count_overrides", {}),
                    additional_vms=vm_customizations.get("additional_vms", []),
                    remove_vms=vm_customizations.get("remove_vms", []),
                    resource_overrides=vm_customizations.get("resource_overrides", {}),
                )
                logger.info("Using custom VM configuration")

        # ALWAYS check and install required roles before deployment
        role_status = {}
        if ensure_roles:
            logger.info("Checking required Ludus roles before deployment...")
            # The authoritative role list lives in the scenario's config, which
            # is not built until further down. Build a throwaway copy here purely
            # to discover the roles - otherwise roles referenced only by the
            # config (ludus.docker, ludus.wifichallenge) are never installed and
            # Ludus rejects the deploy.
            roles_config = None
            try:
                preview = await self.get_scenario_config(scenario_key, siem_type=siem_type)
                roles_config = preview.get("config", preview) if isinstance(preview, dict) else None
            except Exception as e:
                logger.warning(f"Could not pre-build the config for role discovery: {e}")

            role_status = await self.role_manager.ensure_roles_for_scenario(
                scenario_key, auto_install=True, siem_type=siem_type, config=roles_config
            )
            logger.info(f"Role status: {role_status['status']}")

            # Log detailed status
            if role_status.get("installed"):
                logger.info(f"[OK] Installed roles: {', '.join(role_status['installed'])}")
            if role_status.get("missing"):
                logger.warning(f"[WARNING] Missing roles: {', '.join(role_status['missing'])}")
            if role_status.get("install_failed"):
                failed_roles = [f.get("role", "unknown") for f in role_status["install_failed"]]
                logger.warning(
                    f"[WARNING] Failed to install roles: {', '.join(failed_roles)}. "
                    f"Deployment may fail if these roles are required."
                )
                # Provide helpful instructions for directory-based roles
                for failed in role_status["install_failed"]:
                    if failed.get("command"):
                        logger.info(f"  Install manually: {failed['command']}")

        # Build the scenario with SIEM type and resource profile
        # Create a FRESH builder instance to avoid state reuse between deployments
        logger.info(f"Creating fresh builder instance: {builder_class.__name__}")
        builder = builder_class(
            siem_type=siem_type,
            resource_profile=resource_profile,
            customization=customization,
            randomize=is_randomized,
        )
        logger.info(f"Builder created with: SIEM={siem_type}, Profile={resource_profile}, Customized={is_customized}, Randomized={is_randomized}")

        # Set the range name based on scenario key
        range_name = self.RANGE_NAMES.get(scenario_key, scenario_key.replace("-", ""))
        builder.set_range_name(range_name)
        logger.info(f"Set range name: {range_name}")

        # Call the builder method dynamically by name
        logger.info(f"Calling builder method: {builder_method_name}")
        builder_method = getattr(builder, builder_method_name)
        builder_method()

        config = builder.to_dict()

        # Validate configuration was built correctly
        vms = config.get('ludus', [])
        if not vms:
            logger.error(f"ERROR: No VMs in configuration! This should not happen.")
            raise ValueError(f"Scenario {scenario_key} produced empty configuration")

        # Log what we're deploying for verification
        range_name = config.get("name", "Unknown")

        # The Ludus range ID is NOT the scenario's display name. Substituting the
        # display name into "{{ range_id }}" produced VM names that never matched
        # the ones already in the range, so the selective cleanup below kept every
        # existing VM and appended the scenario's on top - duplicating them and
        # tripping "duplicate vlan and ip_last_octet combination found".
        range_id = None
        try:
            range_info = await self.client.get_range(user_id)
            range_id = range_info.get("rangeID")
        except Exception as e:
            logger.warning(f"Could not resolve the range ID ({e}); falling back to the config name")
        range_id = range_id or range_name

        def _resolved(vm_name: str) -> str:
            """Normalise a VM name so both sides of a comparison use the real range ID."""
            return (vm_name or "").replace("{{ range_id }}", range_id).replace("{{range_id}}", range_id)
        logger.info(f"✓ Successfully built scenario: {name}")
        logger.info(f"✓ Range name: {range_name}")
        logger.info(f"✓ Configuration contains {len(vms)} VMs:")
        for vm in vms:
            hostname = vm.get('hostname', 'Unknown')
            template = vm.get('template', 'Unknown')
            vlan = vm.get('vlan', 'Unknown')
            ram = vm.get('ram_gb', 0)
            cpus = vm.get('cpus', 0)
            logger.info(f"  - {hostname} | {template} | VLAN {vlan} | {ram}GB RAM, {cpus} CPUs")
        
        # IMPORTANT: Clean up only scenario-specific VMs before deploying
        # This allows other VMs (from different scenarios or custom configs) to remain
        logger.info(f"Checking for existing scenario VMs to clean up for: {name}")
        try:
            current_config = await self.client.get_range_config(user_id)
            current_vms = current_config.get('ludus', [])
            
            if current_vms and isinstance(current_vms, list) and len(current_vms) > 0:
                # Extract expected VM names from new scenario config
                # VM names in config use {{ range_id }} template, replace with actual range_name
                expected_vm_names = set()
                for vm in vms:
                    vm_name = vm.get('vm_name', '')
                    if vm_name:
                        # Replace {{ range_id }} with actual range_name to get the real VM name
                        expected_vm_names.add(_resolved(vm_name))
                
                if expected_vm_names:
                    # Filter out VMs that match this scenario's VM names
                    # Keep VMs that don't match (from other scenarios or custom configs)
                    vms_to_keep = []
                    vms_to_remove_names = []
                    
                    for current_vm in current_vms:
                        current_vm_name = _resolved(current_vm.get('vm_name', ''))
                        # Check if this VM belongs to this scenario (exact name match)
                        if current_vm_name in expected_vm_names:
                            vms_to_remove_names.append(current_vm_name)
                            logger.info(f"  [REMOVE] Scenario VM: {current_vm_name}")
                        else:
                            vms_to_keep.append(current_vm)
                            logger.info(f"  [KEEP] Non-scenario VM: {current_vm_name}")
                    
                    if vms_to_remove_names:
                        logger.info(f"Selective cleanup: Removing {len(vms_to_remove_names)} scenario VMs, keeping {len(vms_to_keep)} other VMs")
                        # Replace {{ range_id }} in new scenario VMs before merging
                        new_vms_with_replaced_names = []
                        for vm in vms:
                            vm_copy = vm.copy()
                            if 'vm_name' in vm_copy:
                                vm_copy['vm_name'] = _resolved(vm_copy['vm_name'])
                            if 'hostname' in vm_copy:
                                vm_copy['hostname'] = _resolved(vm_copy['hostname'])
                            new_vms_with_replaced_names.append(vm_copy)
                        # Merge: keep existing non-scenario VMs + add new scenario VMs
                        config['ludus'] = vms_to_keep + new_vms_with_replaced_names
                        logger.info(f"Final config: {len(vms_to_keep)} existing VMs + {len(new_vms_with_replaced_names)} new scenario VMs = {len(config['ludus'])} total")
                    elif vms_to_keep:
                        logger.info(f"No scenario VMs to remove, but found {len(vms_to_keep)} other VMs - will merge with new scenario")
                        # Replace {{ range_id }} in new scenario VMs before merging
                        new_vms_with_replaced_names = []
                        for vm in vms:
                            vm_copy = vm.copy()
                            if 'vm_name' in vm_copy:
                                vm_copy['vm_name'] = _resolved(vm_copy['vm_name'])
                            if 'hostname' in vm_copy:
                                vm_copy['hostname'] = _resolved(vm_copy['hostname'])
                            new_vms_with_replaced_names.append(vm_copy)
                        config['ludus'] = vms_to_keep + new_vms_with_replaced_names
                        logger.info(f"Final config: {len(vms_to_keep)} existing VMs + {len(new_vms_with_replaced_names)} new scenario VMs = {len(config['ludus'])} total")
                    else:
                        logger.info("No matching scenario VMs found - deploying fresh scenario")
                        # Replace {{ range_id }} in all VMs
                        for vm in config['ludus']:
                            if 'vm_name' in vm:
                                vm['vm_name'] = _resolved(vm['vm_name'])
                            if 'hostname' in vm:
                                vm['hostname'] = _resolved(vm['hostname'])
                else:
                    logger.info("No VM names in scenario config - deploying fresh")
            else:
                logger.info("No existing VMs found - deploying fresh scenario")
        except Exception as e:
            logger.warning(f"Could not check existing VMs (this is OK for fresh deployments): {e}")
            logger.info("Proceeding with fresh scenario deployment")
        
        # IMPORTANT: Replace {{ range_id }} in all VM names and hostnames before sending
        # This must happen after selective cleanup but before sending to API
        logger.info(f"Replacing {{ range_id }} template with the real range ID: {range_id}")
        for vm in config.get('ludus', []):
            if 'vm_name' in vm:
                vm['vm_name'] = _resolved(vm['vm_name'])
            if 'hostname' in vm:
                vm['hostname'] = _resolved(vm['hostname'])
        
        # IMPORTANT: Set the configuration first, then deploy
        # The Ludus API requires the config to be set via PUT /range/config before deploying
        logger.info(f"Setting range configuration for scenario: {name} (range name: {range_name})")
        logger.info(f"Config contains {len(config.get('ludus', []))} VMs to be set")
        
        try:
            # Log what we're sending
            final_vms = config.get('ludus', [])
            logger.debug(f"Sending config with {len(final_vms)} VMs: {[vm.get('vm_name', 'unknown') for vm in final_vms[:5]]}")
            
            config_result = await self.client.update_range_config(config, user_id)
            logger.info(f"✓ update_range_config API call completed")
            logger.debug(f"Config result: {config_result}")
            
            # CRITICAL: Verify the configuration was actually set
            logger.info(f"Verifying configuration was set correctly...")
            logger.info(f"update_range_config returned: {config_result}")
            await asyncio.sleep(2.0)  # Longer delay to ensure config is persisted (file upload processing)
            
            stored_config = await self.client.get_range_config(user_id)
            logger.info(f"Retrieved stored config - keys: {list(stored_config.keys())}")
            logger.info(f"Stored config type: {type(stored_config)}")
            logger.debug(f"Stored config full: {stored_config}")
            
            # Handle different config formats that Ludus might return
            # Sometimes Ludus returns the config in different structures
            stored_vms = stored_config.get('ludus', [])
            
            # Also check if config is nested differently
            if not stored_vms and isinstance(stored_config, dict):
                # Try alternative locations
                if 'config' in stored_config:
                    stored_vms = stored_config['config'].get('ludus', [])
                elif 'range_config' in stored_config:
                    stored_vms = stored_config['range_config'].get('ludus', [])
            if not isinstance(stored_vms, list):
                # Sometimes Ludus returns config in a different format
                if isinstance(stored_config, dict) and 'ludus' not in stored_config:
                    # Config might be at root level
                    stored_vms = stored_config.get('vms', []) or stored_config.get('VMs', [])
                if not isinstance(stored_vms, list):
                    stored_vms = []
            
            stored_vm_count = len(stored_vms) if isinstance(stored_vms, list) else 0
            
            logger.info(f"Stored config has {stored_vm_count} VMs (expected {len(vms)})")
            
            # Log details for debugging
            # The selective merge above intentionally KEEPS VMs that belong to
            # other scenarios or custom configs, so the stored config can legally
            # hold more VMs than this scenario defines. Only a shortfall means
            # the write failed; the subset check below catches anything missing.
            if stored_vm_count < len(vms):
                logger.error(f"VM COUNT MISMATCH:")
                logger.error(f"  Expected: {len(vms)} VMs")
                logger.error(f"  Stored: {stored_vm_count} VMs")
                if isinstance(stored_vms, list) and stored_vms:
                    logger.error(f"  Stored VM names: {[vm.get('vm_name', 'unknown') for vm in stored_vms[:10]]}")
                logger.error(f"  Expected VM names: {[vm.get('vm_name', 'unknown') for vm in vms[:10]]}")
                
                error_msg = (
                    f"CONFIGURATION VERIFICATION FAILED: "
                    f"Expected at least {len(vms)} VMs but stored config has {stored_vm_count}. "
                    f"The configuration was not properly set in Ludus. "
                    f"Aborting deployment to prevent using incorrect configuration. "
                    f"Please check Ludus API logs for details."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Verify key VMs are present. Both sides must be normalised: `vms`
            # still holds the "{{ range_id }}" template form while the stored
            # config comes back with the range ID resolved, so comparing them raw
            # reported every VM as missing.
            expected_vm_names = {_resolved(vm.get('vm_name')) for vm in vms if vm.get('vm_name')}
            stored_vm_names = {_resolved(vm.get('vm_name')) for vm in stored_vms
                               if isinstance(stored_vms, list) and vm.get('vm_name')}
            
            if expected_vm_names and not expected_vm_names.issubset(stored_vm_names):
                missing = expected_vm_names - stored_vm_names
                error_msg = (
                    f"CONFIGURATION VERIFICATION FAILED: "
                    f"Expected VMs missing from stored config: {missing}. "
                    f"The configuration was not properly set in Ludus."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"✓ Configuration verified: {stored_vm_count} VMs correctly stored")
            logger.info(f"✓ All expected VMs present in stored configuration")
            
        except Exception as e:
            error_msg = f"Failed to set or verify range configuration: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        
        # Deploy using the stored configuration (no config in body)
        logger.info(f"Deploying scenario: {name} with verified configuration")
        result = await self.client.deploy_range(config=None, user_id=user_id)
        
        # Build comprehensive result
        vms = config.get('ludus', [])
        range_name = config.get("name", "Unknown")
        
        # Generate customization summary
        customization_summary = None
        if is_customized or is_randomized:
            summary_parts = []
            if is_randomized:
                summary_parts.append("Randomized configuration")
            if customization and customization.custom_users:
                summary_parts.append(f"{len(customization.custom_users)} custom users")
            if customization and customization.vulnerability_config:
                vuln_count = sum([
                    1 for v in [
                        customization.vulnerability_config.esc1_enabled,
                        customization.vulnerability_config.esc2_enabled,
                        customization.vulnerability_config.esc6_enabled,
                        customization.vulnerability_config.esc8_enabled,
                    ] if v
                ])
                if vuln_count > 0:
                    summary_parts.append(f"{vuln_count} custom vulnerabilities")
            if customization and customization.vm_customization:
                if customization.vm_customization.vm_count_overrides:
                    summary_parts.append("VM count overrides")
            customization_summary = ", ".join(summary_parts) if summary_parts else "Custom configuration"
        
        # Generate walkthrough
        logger.info("Generating scenario walkthrough...")
        walkthrough = generate_scenario_walkthrough(
            scenario_key=scenario_key,
            scenario_name=name,
            config=config,
            customized=is_customized,
            randomized=is_randomized,
            customization_summary=customization_summary,
        )
        logger.info("Walkthrough generated successfully")
        
        deployment_info = {
            "status": "deployment_started",
            "scenario": name,
            "scenario_key": scenario_key,
            "scenario_name": name,  # For backward compatibility
            "range_name": range_name,
            "vm_count": len(vms),
            "deployment_result": result,
            "config": config,
            "role_status": role_status,
            "siem_type": siem_type,
            "resource_profile": resource_profile,
            "walkthrough": walkthrough,  # Comprehensive walkthrough
        }
        
        # Add ADWS timing warning and recovery guidance for AD scenarios
        if "ad" in scenario_key.lower() or any("dc" in vm.get("vm_name", "").lower() for vm in vms):
            deployment_info["adws_note"] = (
                "⚠️  IMPORTANT: Active Directory deployments may show transient ADWS errors during OU configuration.\n"
                "This is NORMAL - AD Web Services takes 5-15 minutes to fully start after domain promotion.\n\n"
                "If deployment fails with 'Unable to find a default server with Active Directory Web Services running':\n"
                "  1. Wait 10-15 minutes for ADWS to start\n"
                "  2. Use handle_adws_recovery() MCP tool to automatically wait and retry\n"
                "  3. Or manually retry: deploy_range(tags='configure,user')\n\n"
                "Ludus will automatically retry failed tasks, but sometimes manual intervention is needed."
            )
            deployment_info["adws_recovery_tool"] = "handle_adws_recovery(wait_minutes=10, auto_retry=True)"
            logger.info("AD scenario detected - ADWS timing issues may occur (normal)")
        
        return deployment_info

    async def get_scenario_config(
        self, scenario_key: str, siem_type: str = "wazuh", resource_profile: str = "recommended"
    ) -> dict[str, Any]:
        """Get scenario configuration without deploying.

        Args:
            scenario_key: Scenario identifier
            siem_type: SIEM type (wazuh, splunk, elastic, security-onion, none)
            resource_profile: Resource profile (minimal, recommended, maximum)

        Returns:
            Scenario configuration dictionary
        """
        if scenario_key not in self.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_key}")

        name, builder_class, builder_method_name, description, vm_summary = self.SCENARIOS[scenario_key]

        # Create a FRESH builder instance to avoid state reuse
        logger.debug(f"[get_scenario_config] Creating fresh {builder_class.__name__} instance")
        builder = builder_class(siem_type=siem_type, resource_profile=resource_profile)
        logger.debug(f"[get_scenario_config] Builder params: SIEM={siem_type}, Profile={resource_profile}")

        # Call the builder method dynamically by name
        logger.debug(f"[get_scenario_config] Calling method: {builder_method_name}")
        builder_method = getattr(builder, builder_method_name)
        builder_method()

        config = builder.to_dict()

        # Validate configuration
        vms = config.get('ludus', [])
        logger.debug(f"[get_scenario_config] Built {name} with {len(vms)} VMs")

        return config

    async def get_scenario_yaml(
        self, scenario_key: str, siem_type: str = "wazuh", resource_profile: str = "minimal"
    ) -> str:
        """Get scenario configuration as YAML."""
        import yaml
        config = await self.get_scenario_config(scenario_key, siem_type, resource_profile)
        yaml_str = "# yaml-language-server: $schema=https://docs.ludus.cloud/schemas/range-config.json\n\n"
        yaml_str += yaml.dump(config, default_flow_style=False, sort_keys=False)
        return yaml_str


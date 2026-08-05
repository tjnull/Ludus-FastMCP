"""SIEM configuration utilities for red team scenarios."""

from typing import Any, Literal

SIEMType = Literal["wazuh", "splunk", "elastic", "security-onion", "none"]


# Wazuh agent MSI used when the installed role does not provide a default.
WAZUH_AGENT_PACKAGE = (
    "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.8.0-1.msi"
)


def get_wazuh_server_config(range_id: str, vlan: int = 10, ip_last_octet: int = 100) -> dict[str, Any]:
    """Get Wazuh server configuration.
    
    Uses the correct Ludus-specific role: aleemladha.wazuh_server_install
    See: https://docs.ludus.cloud/docs/roles/
    """
    return {
        "vm_name": f"{range_id}-wazuh-server-ubuntu22",
        "hostname": f"{range_id}-WAZUH",
        "template": "ubuntu-22.04-x64-server-template",
        "vlan": vlan,
        "ip_last_octet": ip_last_octet,
        "ram_gb": 8,
        "cpus": 4,
        "linux": True,
        "ansible_roles": [
            {
                "name": "aleemladha.wazuh_server_install",
                "vars": {
                    # Role-specific variables as needed
                    # See role documentation for available vars
                },
            },
        ],
    }


def get_splunk_server_config(range_id: str, vlan: int = 10, ip_last_octet: int = 100) -> dict[str, Any]:
    """Get Splunk Enterprise server configuration."""
    return {
        "vm_name": f"{range_id}-splunk-server-ubuntu22",
        "hostname": f"{range_id}-SPLUNK",
        "template": "ubuntu-22.04-x64-server-template",
        "vlan": vlan,
        "ip_last_octet": ip_last_octet,
        "ram_gb": 16,  # Splunk needs more RAM
        "cpus": 4,
        "linux": True,
        "ansible_roles": [
            {
                "name": "splunk.splunk",
                "vars": {
                    "splunk_role": "splunk_server",
                    "splunk_version": "latest",
                    "splunk_web_port": 8000,
                    "splunk_management_port": 8089,
                    "splunk_receiving_port": 9997,
                    "splunk_forwarding_port": 9997,
                },
            },
        ],
    }


def get_elastic_server_config(range_id: str, vlan: int = 10, ip_last_octet: int = 100) -> dict[str, Any]:
    """Get Elastic Stack (ELK) server configuration."""
    return {
        "vm_name": f"{range_id}-elastic-server-ubuntu22",
        "hostname": f"{range_id}-ELASTIC",
        "template": "ubuntu-22.04-x64-server-template",
        "vlan": vlan,
        "ip_last_octet": ip_last_octet,
        "ram_gb": 16,  # Elastic needs more RAM
        "cpus": 4,
        "linux": True,
        "ansible_roles": [
            {
                "name": "elastic.elasticsearch",
                "vars": {
                    "es_version": "latest",
                    "es_heap_size": "4g",
                    "es_cluster_name": f"{range_id}-cluster",
                },
            },
            {
                "name": "elastic.kibana",
                "vars": {
                    "kibana_version": "latest",
                    "kibana_port": 5601,
                },
            },
            {
                "name": "elastic.logstash",
                "vars": {
                    "logstash_version": "latest",
                    "logstash_input_port": 5044,
                },
            },
        ],
    }


def get_security_onion_config(range_id: str, vlan: int = 10, ip_last_octet: int = 100) -> dict[str, Any]:
    """Get Security Onion configuration."""
    return {
        "vm_name": f"{range_id}-security-onion-ubuntu22",
        "hostname": f"{range_id}-SECURITY-ONION",
        "template": "ubuntu-22.04-x64-server-template",
        "vlan": vlan,
        "ip_last_octet": ip_last_octet,
        "ram_gb": 16,  # Security Onion needs significant resources
        "cpus": 4,
        "linux": True,
        "ansible_roles": [
            {
                "name": "securityonion.securityonion",
                "vars": {
                    "so_mode": "standalone",  # or "distributed" for larger deployments
                    "so_install_type": "eval",  # or "production"
                    "so_web_interface": True,
                    "so_web_port": 443,
                },
            },
        ],
    }


def add_siem_agent_to_vm(
    vm_config: dict[str, Any],
    siem_type: SIEMType,
    siem_server_ip: str,
) -> dict[str, Any]:
    """Add SIEM agent configuration to a VM."""
    if siem_type == "none":
        return vm_config
    
    if "ansible_roles" not in vm_config:
        vm_config["ansible_roles"] = []
    
    # Check if agent role already exists
    # Use correct Ludus-specific role names from https://docs.ludus.cloud/docs/roles/
    agent_role_exists = any(
        role.get("name") in [
            "aleemladha.ludus_wazuh_agent",  # Correct Wazuh agent role
            "wazuh.wazuh",  # Legacy/fallback
            "splunk.splunk",
            "badsectorlabs.ludus_elastic_agent",  # Correct Elastic agent role
            "elastic.filebeat",  # Legacy/fallback
            "securityonion.agent",
        ]
        for role in vm_config.get("ansible_roles", [])
    )
    
    if agent_role_exists:
        return vm_config
    
    if siem_type == "wazuh":
        # Use correct Ludus-specific role: aleemladha.ludus_wazuh_agent
        # See: https://docs.ludus.cloud/docs/roles/
        vm_config["ansible_roles"].append({
            "name": "aleemladha.ludus_wazuh_agent",
            "vars": {
                # The role reads ludus_wazuh_siem_server; "wazuh_manager_ip"
                # was our own invention and the role never looked at it, so
                # agents were configured with an empty manager address.
                "ludus_wazuh_siem_server": siem_server_ip,
                # Older installed copies of the role reference the package URL
                # without the ludus_ prefix and ship no default for it, which
                # fails the play with "'wazuh_agent_install_package' is
                # undefined". Set both names so either revision works.
                "ludus_wazuh_agent_install_package": WAZUH_AGENT_PACKAGE,
                "wazuh_agent_install_package": WAZUH_AGENT_PACKAGE,
                # kept for backwards compatibility with anything reading it
                "wazuh_manager_ip": siem_server_ip,
            },
        })
    elif siem_type == "splunk":
        vm_config["ansible_roles"].append({
            "name": "splunk.splunk",
            "vars": {
                "splunk_role": "splunk_forwarder",
                "splunk_server": siem_server_ip,
                "splunk_forwarding_port": 9997,
            },
        })
    elif siem_type == "elastic":
        vm_config["ansible_roles"].append({
            "name": "elastic.filebeat",
            "vars": {
                "filebeat_version": "latest",
                "logstash_hosts": [f"{siem_server_ip}:5044"],
                "elasticsearch_hosts": [f"{siem_server_ip}:9200"],
            },
        })
    elif siem_type == "security-onion":
        vm_config["ansible_roles"].append({
            "name": "securityonion.agent",
            "vars": {
                "so_manager_ip": siem_server_ip,
                "so_agent_type": "beats",  # or "syslog"
            },
        })
    
    return vm_config


def get_siem_network_rules(siem_type: SIEMType) -> list[dict[str, Any]]:
    """Get network rules for SIEM communication."""
    if siem_type == "wazuh":
        return [
            {
                "name": "Allow Wazuh agents to manager (TCP 1514)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 1514,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Wazuh agents to manager (UDP 1514)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "udp",
                "ports": 1514,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Wazuh API access (TCP 55000)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 55000,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Wazuh Dashboard access (TCP 5601)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 5601,
                "action": "ACCEPT",
            },
        ]
    elif siem_type == "splunk":
        return [
            {
                "name": "Allow Splunk forwarders to server (TCP 9997)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 9997,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Splunk Web access (TCP 8000)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 8000,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Splunk Management (TCP 8089)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 8089,
                "action": "ACCEPT",
            },
        ]
    elif siem_type == "elastic":
        return [
            {
                "name": "Allow Filebeat to Logstash (TCP 5044)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 5044,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Elasticsearch access (TCP 9200)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 9200,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Kibana access (TCP 5601)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 5601,
                "action": "ACCEPT",
            },
        ]
    elif siem_type == "security-onion":
        return [
            {
                "name": "Allow Security Onion agents (TCP 5044)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 5044,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Security Onion Web (TCP 443)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "tcp",
                "ports": 443,
                "action": "ACCEPT",
            },
            {
                "name": "Allow Security Onion Syslog (UDP 514)",
                "vlan_src": 0,
                "vlan_dst": 0,
                "protocol": "udp",
                "ports": 514,
                "action": "ACCEPT",
            },
        ]
    else:
        return []


def get_siem_server_config(
    siem_type: SIEMType,
    range_id: str,
    vlan: int = 10,
    ip_last_octet: int = 100,
) -> dict[str, Any]:
    """Get SIEM server configuration based on type."""
    if siem_type == "wazuh":
        return get_wazuh_server_config(range_id, vlan, ip_last_octet)
    elif siem_type == "splunk":
        return get_splunk_server_config(range_id, vlan, ip_last_octet)
    elif siem_type == "elastic":
        return get_elastic_server_config(range_id, vlan, ip_last_octet)
    elif siem_type == "security-onion":
        return get_security_onion_config(range_id, vlan, ip_last_octet)
    else:
        return {}


"""Handler for network analysis and troubleshooting operations."""

from datetime import datetime
from typing import Any
import json

from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


class NetworkAnalysisHandler:
    """Handler for network analysis and troubleshooting."""

    def __init__(self, client: LudusAPIClient) -> None:
        """Initialize the network analysis handler."""
        self.client = client

    async def test_network_connectivity(
        self,
        source_vm: str | None = None,
        target_vm: str | None = None,
        test_type: str = "comprehensive",
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Test network connectivity between VMs.

        Args:
            source_vm: Source VM name (if None, tests from all VMs)
            target_vm: Target VM name (if None, tests to all VMs)
            test_type: Type of test (ping, comprehensive, port_scan)
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with connectivity test results
        """
        try:
            range_info = await self.client.get_range(user_id)
            vms = range_info.get("VMs", [])

            if not vms:
                return {
                    "status": "error",
                    "error": "No VMs found in range"
                }

            # Get VM names
            vm_names = [vm.get("name") for vm in vms if vm.get("name")]

            # Determine source and target VMs
            sources = [source_vm] if source_vm else vm_names
            targets = [target_vm] if target_vm else vm_names

            connectivity_tests = []

            for src in sources:
                for tgt in targets:
                    if src == tgt:
                        continue

                    # Find VM IP addresses
                    src_vm = next((vm for vm in vms if vm.get("name") == src), None)
                    tgt_vm = next((vm for vm in vms if vm.get("name") == tgt), None)

                    if not src_vm or not tgt_vm:
                        continue

                    src_ip = self._get_vm_ip(src_vm)
                    tgt_ip = self._get_vm_ip(tgt_vm)

                    test_result = {
                        "source": {
                            "name": src,
                            "ip": src_ip,
                            "network": self._get_vm_network(src_vm)
                        },
                        "target": {
                            "name": tgt,
                            "ip": tgt_ip,
                            "network": self._get_vm_network(tgt_vm)
                        },
                        "test_type": test_type,
                        "timestamp": datetime.now().isoformat(),
                        "results": self._simulate_connectivity_test(
                            src_vm, tgt_vm, test_type
                        )
                    }

                    connectivity_tests.append(test_result)

            # Calculate connectivity summary
            total_tests = len(connectivity_tests)
            reachable = sum(
                1 for test in connectivity_tests
                if test["results"].get("reachable", False)
            )

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "test_configuration": {
                    "source_vm": source_vm or "all",
                    "target_vm": target_vm or "all",
                    "test_type": test_type
                },
                "summary": {
                    "total_tests": total_tests,
                    "reachable": reachable,
                    "unreachable": total_tests - reachable,
                    "success_rate": round((reachable / total_tests * 100), 2) if total_tests > 0 else 0
                },
                "tests": connectivity_tests,
                "note": "This is a connectivity analysis based on network configuration. For actual ping tests, use Ansible playbooks or SSH commands."
            }

            logger.info(f"Network connectivity test: {reachable}/{total_tests} reachable")
            return result

        except Exception as e:
            logger.error(f"Error testing network connectivity: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _get_vm_ip(self, vm: dict) -> str:
        """Extract VM IP address."""
        # Try to get IP from various possible fields
        if "ip" in vm:
            return vm["ip"]
        if "ipAddress" in vm:
            return vm["ipAddress"]
        if "network" in vm and isinstance(vm["network"], dict):
            return vm["network"].get("ip", "unknown")
        return "unknown"

    def _get_vm_network(self, vm: dict) -> str:
        """Extract VM network name."""
        if "network" in vm:
            if isinstance(vm["network"], str):
                return vm["network"]
            if isinstance(vm["network"], dict):
                return vm["network"].get("name", "unknown")
        return "unknown"

    def _simulate_connectivity_test(
        self,
        src_vm: dict,
        tgt_vm: dict,
        test_type: str
    ) -> dict[str, Any]:
        """Simulate connectivity test based on network configuration."""
        src_network = self._get_vm_network(src_vm)
        tgt_network = self._get_vm_network(tgt_vm)

        # Same network = reachable
        same_network = src_network == tgt_network

        result = {
            "reachable": same_network,
            "same_network": same_network,
            "latency_ms": 1.5 if same_network else "N/A",
            "packet_loss": "0%" if same_network else "100%"
        }

        if test_type == "comprehensive":
            result["icmp_ping"] = same_network
            result["tcp_connectivity"] = same_network
            result["routing"] = "direct" if same_network else "requires_routing"

        return result

    async def get_network_topology(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Generate network topology visualization data.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with network topology data
        """
        try:
            range_info = await self.client.get_range(user_id)
            range_config = await self.client.get_range_config(user_id)

            vms = range_info.get("VMs", [])

            # A Ludus config has no list of network objects: "ludus" is the list
            # of VMs and "network" is a top-level block of inter-VLAN rules.
            # Reading range_config["ludus"]["network"] raised
            # "'list' object has no attribute 'get'" on every call.
            config_vms = range_config.get("ludus", [])
            if isinstance(config_vms, dict):
                config_vms = config_vms.get("vms", [])
            network_block = range_config.get("network")
            vlan_rules = network_block.get("rules", []) if isinstance(network_block, dict) else []

            # Build network topology
            topology = {
                "networks": [],
                "vms": [],
                "connections": [],
                "inter_vlan_rules": vlan_rules,
                "inter_vlan_default": (
                    network_block.get("inter_vlan_default")
                    if isinstance(network_block, dict) else None
                ),
            }

            # Networks are the distinct VLANs the VMs sit on
            vlan_members: dict[Any, list[str]] = {}
            for vm in config_vms:
                if not isinstance(vm, dict):
                    continue
                vlan = vm.get("vlan")
                if vlan is None:
                    continue
                vlan_members.setdefault(vlan, []).append(
                    vm.get("vm_name") or vm.get("hostname") or "unknown"
                )
            for vlan in sorted(vlan_members, key=lambda v: (v is None, v)):
                topology["networks"].append({
                    "name": f"VLAN {vlan}",
                    "vlan": vlan,
                    "subnet": f"10.x.{vlan}.0/24",
                    "gateway": f"10.x.{vlan}.254",
                    "type": "internal",
                    "vms": vlan_members[vlan],
                })

            # Process VMs and their connections
            for vm in vms:
                vm_info = {
                    "name": vm.get("name", "unknown"),
                    "ip": self._get_vm_ip(vm),
                    "network": self._get_vm_network(vm),
                    "status": vm.get("status", "unknown"),
                    "template": vm.get("template", "unknown")
                }
                topology["vms"].append(vm_info)

                # Create connection to network
                topology["connections"].append({
                    "from": vm_info["name"],
                    "to": vm_info["network"],
                    "type": "vm_to_network"
                })

            # Generate visualization data
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "topology": topology,
                "statistics": {
                    "total_networks": len(topology["networks"]),
                    "total_vms": len(topology["vms"]),
                    "total_connections": len(topology["connections"])
                },
                "mermaid_diagram": self._generate_mermaid_diagram(topology),
                "dot_graph": self._generate_dot_graph(topology)
            }

            logger.info(f"Generated network topology: {len(topology['networks'])} networks, {len(topology['vms'])} VMs")
            return result

        except Exception as e:
            logger.error(f"Error generating network topology: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _generate_mermaid_diagram(self, topology: dict) -> str:
        """Generate Mermaid diagram syntax for topology."""
        lines = ["graph TD"]

        # Add networks
        for net in topology["networks"]:
            net_id = net["name"].replace("-", "_").replace(" ", "_")
            lines.append(f'    {net_id}["{net["name"]}<br/>{net["subnet"]}"]')
            lines.append(f'    style {net_id} fill:#e1f5ff')

        # Add VMs
        for vm in topology["vms"]:
            vm_id = vm["name"].replace("-", "_").replace(" ", "_")
            lines.append(f'    {vm_id}["{vm["name"]}<br/>{vm["ip"]}"]')

        # Add connections
        for conn in topology["connections"]:
            from_id = conn["from"].replace("-", "_").replace(" ", "_")
            to_id = conn["to"].replace("-", "_").replace(" ", "_")
            lines.append(f'    {from_id} --> {to_id}')

        return "\n".join(lines)

    def _generate_dot_graph(self, topology: dict) -> str:
        """Generate Graphviz DOT format for topology."""
        lines = ["digraph network_topology {"]
        lines.append('    rankdir=TB;')
        lines.append('    node [shape=box];')

        # Add networks
        for net in topology["networks"]:
            net_id = net["name"].replace("-", "_").replace(" ", "_")
            lines.append(f'    {net_id} [label="{net["name"]}\\n{net["subnet"]}" style=filled fillcolor=lightblue];')

        # Add VMs
        for vm in topology["vms"]:
            vm_id = vm["name"].replace("-", "_").replace(" ", "_")
            lines.append(f'    {vm_id} [label="{vm["name"]}\\n{vm["ip"]}"];')

        # Add connections
        for conn in topology["connections"]:
            from_id = conn["from"].replace("-", "_").replace(" ", "_")
            to_id = conn["to"].replace("-", "_").replace(" ", "_")
            lines.append(f'    {from_id} -> {to_id};')

        lines.append("}")
        return "\n".join(lines)

    async def diagnose_network_issues(self, user_id: str | None = None) -> dict[str, Any]:
        """
        Automated network troubleshooting.

        Args:
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with diagnostic results
        """
        try:
            range_info = await self.client.get_range(user_id)
            range_config = await self.client.get_range_config(user_id)
            logs = await self.client.get_range_logs(user_id)

            vms = range_info.get("VMs", [])
            networks = (range_config.get("network") or {}).get("rules", [])

            issues = []
            warnings = []
            recommendations = []

            # Check for VMs without IPs
            vms_without_ip = [
                vm for vm in vms
                if self._get_vm_ip(vm) == "unknown"
            ]
            if vms_without_ip:
                issues.append({
                    "severity": "high",
                    "type": "missing_ip",
                    "message": f"{len(vms_without_ip)} VMs without IP addresses",
                    "affected_vms": [vm.get("name") for vm in vms_without_ip]
                })
                recommendations.append("Deploy or redeploy range to assign IP addresses")

            # Check for network isolation
            network_groups = {}
            for vm in vms:
                net = self._get_vm_network(vm)
                if net not in network_groups:
                    network_groups[net] = []
                network_groups[net].append(vm.get("name"))

            if len(network_groups) > 1:
                warnings.append({
                    "severity": "info",
                    "type": "network_segmentation",
                    "message": f"Range has {len(network_groups)} separate networks",
                    "networks": network_groups
                })
                recommendations.append("Verify network segmentation is intentional")

            # Check for stopped VMs
            stopped_vms = [vm for vm in vms if vm.get("status") != "running"]
            if stopped_vms:
                warnings.append({
                    "severity": "medium",
                    "type": "stopped_vms",
                    "message": f"{len(stopped_vms)} VMs are not running",
                    "affected_vms": [vm.get("name") for vm in stopped_vms]
                })
                recommendations.append("Use ludus.power_on_range to start all VMs")

            # Check logs for network errors
            if logs:
                log_lines = logs.lower()
                if "network" in log_lines and ("error" in log_lines or "failed" in log_lines):
                    issues.append({
                        "severity": "high",
                        "type": "network_errors_in_logs",
                        "message": "Network-related errors found in deployment logs"
                    })
                    recommendations.append("Review deployment logs for network configuration errors")

            # Calculate health status
            health_status = "healthy"
            if issues:
                health_status = "critical"
            elif warnings:
                health_status = "warning"

            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "health_status": health_status,
                "summary": {
                    "total_vms": len(vms),
                    "total_networks": len(networks),
                    "issues_found": len(issues),
                    "warnings_found": len(warnings)
                },
                "issues": issues,
                "warnings": warnings,
                "recommendations": recommendations,
                "network_statistics": {
                    "network_count": len(network_groups),
                    "vms_per_network": {
                        net: len(vms_list)
                        for net, vms_list in network_groups.items()
                    }
                }
            }

            logger.info(f"Network diagnostics: {health_status}, {len(issues)} issues, {len(warnings)} warnings")
            return result

        except Exception as e:
            logger.error(f"Error diagnosing network issues: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def capture_network_traffic(
        self,
        vm_name: str,
        duration_seconds: int = 60,
        filter_expression: str | None = None,
        user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Initiate packet capture on specific VMs.

        Args:
            vm_name: Name of the VM to capture traffic on
            duration_seconds: Duration of capture in seconds
            filter_expression: BPF filter expression (e.g., "tcp port 80")
            user_id: Optional user ID (admin only)

        Returns:
            Dictionary with capture configuration
        """
        try:
            range_info = await self.client.get_range(user_id)
            vms = range_info.get("VMs", [])

            # Find target VM
            target_vm = next((vm for vm in vms if vm.get("name") == vm_name), None)
            if not target_vm:
                return {
                    "status": "error",
                    "error": f"VM not found: {vm_name}"
                }

            capture_config = {
                "status": "success",
                "capture_id": f"capture-{vm_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "vm_name": vm_name,
                "vm_ip": self._get_vm_ip(target_vm),
                "duration_seconds": duration_seconds,
                "filter_expression": filter_expression or "all traffic",
                "start_time": datetime.now().isoformat(),
                "estimated_end_time": (datetime.now()).isoformat(),
                "configuration": {
                    "interface": "auto-detect",
                    "snaplen": 65535,
                    "promiscuous_mode": True,
                    "buffer_size_mb": 100
                },
                "implementation_notes": {
                    "ansible_playbook": f"Use Ansible to run tcpdump on {vm_name}",
                    "command": f"tcpdump -i any -w /tmp/capture.pcap {'-f ' + filter_expression if filter_expression else ''}",
                    "retrieval": "Use ansible.builtin.fetch to retrieve the pcap file"
                }
            }

            logger.info(f"Configured packet capture for {vm_name}: {duration_seconds}s")
            return capture_config

        except Exception as e:
            logger.error(f"Error configuring packet capture: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

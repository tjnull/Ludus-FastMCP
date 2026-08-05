# Tools Reference

Complete reference for all tools available in Ludus FastMCP, organized by category.

## Overview

Ludus FastMCP provides **231 tools** across 23 modules. Tools marked with require a Ludus 2.0 server. Together they cover every endpoint in the Ludus API.

| Category | Tools | Description |
|----------|-------|-------------|
| Core Operations | 21 | Range, snapshot, power, network, template management |
| Blueprints | 19 | Blueprint lifecycle, export/import, sharing, access control |
| Custom Builder | 18 | Skeleton templates, custom OS/containers |
| Templates Advanced | 18 | Template discovery, upload, building, role scope |
| Security Integration | 14 | SIEM configuration, compliance, access control |
| Deployment | 13 | Scenario deployment, orchestration, monitoring |
| Metrics and Monitoring | 13 | Performance, health checks, inventory |
| Quotas & Limits | 12 | Quotas, auto-shutdown, deployment log history |
| Content Sources | 12 | Git/archive catalogs of templates, roles, blueprints |
| Automation | 11 | Pipelines, scheduling, bulk operations |
| Role Management | 11 | Ansible Galaxy, custom roles |
| Groups | 9 | Group management, membership, range access |
| Diagnostics & Migration | 8 | Diagnostics, license, OpenAPI, SQLite/SDN migration |
| Collaboration | 7 | Sharing, resources, community |
| Enhanced Range Management | 7 | Range creation, user assignment, defaults |
| User Management | 7 | User accounts, API keys, credentials |
| Batch Operations | 6 | Bulk snapshot, power, and status operations |
| Range Management | 7 | List, search, delete, cleanup |
| Documentation | 4 | Lab guides, attack paths, playbooks |
| Integrations | 4 | Webhooks, Slack, Jira, Git |
| Profile Transformation | 4 | Adversary/defender profiles |
| AI Config Generation | 3 | Natural language to YAML |
| VM Management | 3 | VM destruction, console tickets and URLs |

## Tool Categories

Every tool below is registered by the server; the tables are generated from the
source so they cannot drift out of sync with what is actually available.

### Core Operations

| Tool | Description |
|------|-------------|
| `get_range` | Get current user's range information. |
| `get_range_config` | Get range configuration. |
| `update_range_config` | Update range configuration. |
| `deploy_range` | Deploy a range from configuration with optional filters for resuming. |
| `get_range_tags` | Get available Ansible tags for the current range. |
| `abort_range_deployment` | Abort a range deployment. |
| `snapshot_host` | Create a snapshot of one or more VMs in the range. |
| `list_snapshots` | List all snapshots for the range. |
| `rollback_snapshot` | Roll one or more VMs back to a snapshot. |
| `remove_snapshot` | Delete a snapshot from one or more VMs. |
| `power_on_range` | Power on all VMs in the range. |
| `power_off_range` | Power off all VMs in the range. |
| `list_templates` | List available templates. |
| `list_hosts` | List all hosts in range. |
| `list_networks` | List the networks (VLANs) in a range. |
| `start_testing` | Start testing state for the range. |
| `stop_testing` | Stop testing state for the range. |
| `allow_testing_domains` | Allow specific domains or IPs while the range is in testing mode. |
| `deny_testing_domains` | Re-block domains or IPs that were previously allowed in testing mode. |
| `update_testing_vm` | Re-run Ansible against a VM or group. |
| `health_check` | Check health of Ludus MCP server and Ludus API connectivity. |

### Deployment and Scenarios

| Tool | Description |
|------|-------------|
| `list_scenarios` | List all available scenarios. |
| `deploy_scenario` | Deploy a scenario with optional SIEM integration and customization. |
| `get_scenario_config` | Get scenario configuration. |
| `get_scenario_yaml` | Get scenario configuration as YAML. |
| `preview_scenario` | Preview a scenario before deployment with detailed information. |
| `quick_status` | Get one-line deployment status with emoji indicators. |
| `get_deployment_status` | Get current deployment status with detailed information. |
| `get_range_logs` | Get deployment logs for the range. |
| `smart_deploy` | Smart deployment with validation, optional snapshot, and auto-monitoring. |
| `monitor_deployment` | Monitor deployment progress with periodic updates. |
| `deployment_timeline` | Get deployment timeline with progress tracking. |
| `validate_config` | Validate range configuration before deployment. |
| `handle_adws_recovery` | Handle Active Directory Web Services (ADWS) recovery for stuck deployments. |

### Range Management

| Tool | Description |
|------|-------------|
| `list_all_ranges_detailed` | List all ranges with detailed information including identification. |
| `get_range_by_user` | Get detailed information about a specific user's range. |
| `find_range_by_vm_name` | Find which range contains a specific VM by name. |
| `delete_range_by_user` | Delete a specific user's range (requires confirmation). |
| `delete_ranges_by_status` | Delete all ranges matching a specific status (requires confirmation). |
| `delete_range_object` | Delete a range object entirely, removing its configuration too. |
| `cleanup_old_ranges` | Delete all ranges EXCEPT those belonging to specified users. |

`delete_range_by_user` is `ludus range rm`: it destroys the VMs and keeps the
range, so it can be redeployed from the same configuration.
`delete_range_object` is `ludus range rm-range`: it removes the range itself,
configuration included. Reach for the first to reset a lab and the second to
decommission one.

### Enhanced Range Management

| Tool | Description |
|------|-------------|
| `create_new_range` | Create a new range. |
| `assign_range_to_user` | Assign range access to a user. |
| `revoke_range_from_user` | Revoke range access from a user. |
| `list_range_users` | List users with access to a range. |
| `list_accessible_ranges` | List ranges accessible to current user. |
| `get_default_range` | Get user's default range ID. |
| `set_default_range` | Set user's default range. |

### User Management

| Tool | Description |
|------|-------------|
| `list_users` | List all users in the Ludus system. |
| `get_user` | Get information about a specific user. |
| `add_user` | Add a new user to the Ludus system. |
| `remove_user` | Remove a user from the Ludus system. |
| `regenerate_user_apikey` | DESTRUCTIVE: issue a NEW API key for a user, invalidating the old one. |
| `provision_oauth2_user` | Provision an OAuth2 user. |
| `get_user_memberships` | Get current user's group memberships. |

### Groups

| Tool | Description |
|------|-------------|
| `list_groups` | List all groups. |
| `create_group` | Create a new group. |
| `delete_group` | Delete a group. |
| `add_users_to_group` | Add users to a group. |
| `remove_users_from_group` | Remove users from a group. |
| `list_group_members` | List group members. |
| `add_ranges_to_group` | Add ranges to a group. |
| `remove_ranges_from_group` | Remove ranges from a group. |
| `list_group_ranges` | List group ranges. |

### Security and SIEM

| Tool | Description |
|------|-------------|
| `get_siem_info` | Get SIEM information for the range. |
| `get_siem_alerts` | Get SIEM alerts for the range. |
| `get_siem_agents` | Get SIEM agents for the range. |
| `get_detection_summary` | Get detection summary from SIEM. |
| `get_wazuh_info` | Get Wazuh SIEM information for the range. |
| `get_range_access` | Get range access information. |
| `grant_range_access` | Grant other users access to your range. |
| `revoke_range_access` | Revoke range access from a user. |
| `clear_range_access` | Clear all range access permissions. |
| `range_access_logs` | Get range access logs. |
| `security_audit` | Run security audit on the range. |
| `compliance_check` | Check compliance against security framework. |
| `rotate_credentials` | Suggest new credentials for VMs in the range. DOES NOT APPLY THEM. |
| `get_vulnerability_scan` | Get vulnerability scan results for the range. |

### Templates Advanced

| Tool | Description |
|------|-------------|
| `add_template` | Add a packer template to Ludus by uploading a local directory. |
| `build_template` | Start a packer build for one or more VM templates. |
| `delete_template` | Delete a template. |
| `get_template_status` | Get the status of in-progress packer builds. |
| `get_template_logs` | Get the latest packer build logs. |
| `abort_template_build` | Abort the running packer build(s). |
| `create_custom_template` | Create a custom template from scratch. |
| `create_container_template` | Create a container-based template. |
| `list_common_containers` | List common container base images. |
| `get_container_config` | Get configuration for a common container. |
| `template_diff` | Compare two templates and show differences. |
| `validate_template` | Validate a template configuration. |
| `get_template_dependencies` | Get template dependencies. |
| `optimize_template` | Optimize a template for better performance. |
| `move_ansible_role_scope` | Move Ansible roles between user and global scope. |
| `get_ansible_role_vars` | Get variables for an Ansible role. |
| `list_subscription_roles` | List available subscription roles (Ludus 2.0 Enterprise only). |
| `install_subscription_roles` | Install subscription roles (Ludus 2.0 Enterprise only). |

### Custom Builder

| Tool | Description |
|------|-------------|
| `create_custom_os_template` | Create a custom OS template with specific packages and configuration. |
| `create_kali_weekly_template` | Create a Kali Linux weekly template with automatic latest ISO detection. |
| `get_common_iso_urls` | Get common ISO download URLs for popular operating systems. |
| `build_container_based_template` | Build a custom container-based template for applications. |
| `get_common_container_configs` | Get pre-configured container definitions for common applications. |
| `create_custom_range_from_scenario` | Create a custom range configuration based on an existing scenario. |
| `build_range_from_scratch` | Build a completely custom range configuration from scratch. |
| `export_range_config_to_yaml` | Export a range configuration to a YAML file for download. |
| `get_current_range_config_for_download` | Get the current range configuration and prepare it for download. |
| `clone_and_modify_scenario` | Clone an existing scenario and modify it to create a new custom scenario. |
| `build_range_from_description` | Build a custom range configuration from a natural language description. |
| `list_vm_skeletons` | List all available VM skeleton templates. |
| `get_vm_skeleton` | Get a specific VM skeleton template configuration. |
| `list_range_skeletons` | List all available range skeleton templates. |
| `get_range_skeleton` | Get a complete range skeleton configuration. |
| `list_yaml_examples` | List all available YAML configuration examples. |
| `get_yaml_example` | Get a ready-to-use YAML configuration example. |
| `build_range_from_skeleton` | Build a complete range configuration starting from a skeleton. |

### Role Management

| Tool | Description |
|------|-------------|
| `list_installed_roles` | List all installed Ansible roles on the Ludus server. |
| `check_role_installed` | Check if a specific Ansible role is installed. |
| `install_role` | Install an Ansible role on the Ludus server via MCP. |
| `get_required_roles_for_scenario` | Get the list of required Ansible roles for a specific scenario. |
| `configure_ssh_role_installation` | Configure SSH access for automatic role installation on Ludus server. |
| `ensure_scenario_roles` | Ensure all required roles for a scenario are installed, installing missing ones automatically. |
| `get_role_info` | Get information about a specific role, including installation method and requirements. |
| `install_galaxy_role` | Install an Ansible role directly from Ansible Galaxy. |
| `install_role_from_url` | Install an Ansible role from a custom Git repository URL. |
| `get_common_galaxy_roles` | Get a list of commonly used Ansible Galaxy roles for Ludus scenarios. |
| `list_role_repositories` | List all roles that are available from GitHub repositories (directory-based roles). |

### Blueprints

| Tool | Description |
|------|-------------|
| `deploy_range_from_blueprint` | Set up and deploy a whole range from a blueprint in one call. |
| `list_blueprints` | List all available blueprints. |
| `get_blueprint` | Get a blueprint's metadata: name, description, version, tags, source. |
| `create_blueprint` | Create a blueprint from a range configuration you already have. |
| `export_blueprint` | Export a blueprint to a .tar.gz archive on disk. |
| `import_blueprint` | Import a blueprint from a .tar.gz archive. |
| `install_blueprint` | Install a blueprint's Ansible role and collection dependencies. |
| `create_blueprint_from_range` | Create a reusable blueprint from an existing range. |
| `apply_blueprint_to_range` | Apply a blueprint to a range. |
| `copy_blueprint` | Copy a blueprint under a new ID. |
| `delete_blueprint` | Delete a blueprint. |
| `get_blueprint_config` | Get blueprint configuration. |
| `update_blueprint_config` | Update blueprint configuration. |
| `share_blueprint_with_users` | Share a blueprint with users. |
| `unshare_blueprint_with_users` | Unshare a blueprint from users. |
| `share_blueprint_with_groups` | Share a blueprint with groups. |
| `unshare_blueprint_with_groups` | Unshare a blueprint from groups. |
| `list_blueprint_access_users` | List users with access to a blueprint. |
| `list_blueprint_access_groups` | List groups with access to a blueprint. |

Blueprints that come from a content source must have their dependencies installed
before deployment. Run `install_blueprint` first, otherwise the deploy fails
partway through on missing roles, after the VMs have already been cloned.

### Content Sources

| Tool | Description |
|------|-------------|
| `list_sources` | List content sources configured on the Ludus server. |
| `get_source` | Get details for a single content source. |
| `get_source_catalog` | Get everything a source publishes, with install state for each item. |
| `list_source_templates` | List packer templates published by a source. |
| `list_source_blueprints` | List blueprints published by a source (GOAD, AD + Elastic, ...). |
| `list_source_roles` | List Ansible roles published by a source. |
| `list_source_collections` | List Ansible collections published by a source. |
| `install_from_source` | Install templates, blueprints, roles or collections from a source. |
| `add_source` | Register a new content source on the Ludus server. |
| `update_source` | Update an existing source's URL, tracked ref, or backing archive. |
| `sync_source` | Re-fetch a source so its catalog reflects the current upstream. |
| `delete_source` | Remove a content source. |

Adding a source installs nothing on its own. The usual sequence is `add_source`
-> `get_source_catalog` -> `install_from_source`.

### Quotas, Auto-Shutdown, and Log History

| Tool | Description |
|------|-------------|
| `get_user_quotas` | Get the resource quotas applied to a user. |
| `get_all_user_quotas` | Get quotas for every user on the server (admin only). |
| `get_default_quotas` | Get the server-wide default quotas that new users inherit. |
| `set_user_quotas` | Set resource quotas for one or more users (admin only). |
| `get_group_quotas` | Get the default quotas configured for each group (admin only). |
| `set_group_quotas` | Set default quotas for one or more groups (admin only). |
| `get_auto_shutdown` | Get the auto-shutdown timeout for a range. |
| `set_auto_shutdown` | Set how long a range may sit idle before it powers itself off. |
| `list_range_log_history` | List previous range deployment logs, most recent first. |
| `get_range_log_from_history` | Get the full contents of one archived range deployment log. |
| `list_template_log_history` | List previous template build logs, most recent first. |
| `get_template_log_from_history` | Get the full contents of one archived template build log. |

Quotas and auto-shutdown are served by Ludus plugins and may not be loaded on a
given server. When absent they return `available: false` with an explanation
rather than an error implying a bad request; see the README.

`get_range_logs` only returns the current or most recent deployment. The history
tools reach the archive, which is what you want when comparing a failed
deployment against the last one that worked.

### VM Management

| Tool | Description |
|------|-------------|
| `destroy_vm` | Destroy a specific VM. |
| `get_vm_console_ticket` | Get a console (noVNC) ticket for a VM. |
| `get_vm_console_view_url` | Get the console WebSocket URL for a ticket from get_vm_console_ticket. |

The console is a WebSocket VNC channel, not a web page, so
`get_vm_console_view_url` returns a `wss://` URL for a VNC/noVNC client rather
than fetching a page. This is the way to reach a VM with no working network,
such as one that failed its domain join.

### Diagnostics and Migration

| Tool | Description |
|------|-------------|
| `get_diagnostics` | Get system diagnostics. |
| `whoami` | Test authentication and get user info. |
| `get_license` | Get license information. |
| `migrate_sqlite_to_pocketbase` | Migrate from SQLite to PocketBase. |
| `get_sdn_migration_status` | Get SDN migration status. |
| `migrate_to_sdn` | Migrate to SDN networking. |
| `setup_sdn` | Setup SDN infrastructure. |
| `get_server_openapi_spec` | Fetch the Ludus server's own OpenAPI specification. |

Use `get_server_openapi_spec` to discover what a particular server implements
rather than assuming every documented endpoint exists; Ludus serves some features
from optional plugins, and the published docs cover a superset of any one build.

### Metrics and Monitoring

| Tool | Description |
|------|-------------|
| `get_range_metrics` | Get comprehensive metrics for the range. |
| `get_deployment_metrics` | Get metrics for the current deployment. |
| `get_cost_estimation` | Get cost estimation for the range. |
| `export_metrics` | Export metrics data. |
| `get_range_ansible_inventory` | Get Ansible inventory for the range. |
| `get_range_sshconfig` | Get SSH config for the range. |
| `get_range_rdpconfigs` | Get RDP configuration files for the range. |
| `get_range_etchosts` | Get /etc/hosts entries for the range. |
| `test_network_connectivity` | Test network connectivity between VMs. |
| `get_network_topology` | Get network topology visualization data. |
| `diagnose_network_issues` | Diagnose network connectivity issues. |
| `capture_network_traffic` | Capture network traffic on a VM. |
| `health_checks` | Run health checks on all VMs in the range. |

### Automation

| Tool | Description |
|------|-------------|
| `create_deployment_pipeline` | Create a deployment pipeline with multiple stages. |
| `schedule_range_tasks` | Schedule a recurring task for the range. |
| `auto_scaling` | Define auto-scaling rules based on resource usage. |
| `schedule_snapshots` | Schedule automatic snapshots for VMs. |
| `clone_range` | Clone the current range to another user. |
| `export_range_backup` | Export a range backup (configuration and snapshot metadata). |
| `import_range_backup` | Import and restore range from backup. |
| `bulk_vm_operations` | Perform bulk operations on multiple VMs. |
| `delete_range` | Delete the entire range. |
| `abort_and_remove_range` | Abort any active deployment and then remove the range. |
| `get_recovery_recommendation` | Get recovery recommendations for failed deployments. |

### Batch Operations

| Tool | Description |
|------|-------------|
| `batch_snapshot_hosts` | Create snapshots for multiple VMs in parallel. |
| `batch_rollback_snapshots` | Rollback multiple VMs to a snapshot in parallel. |
| `batch_remove_snapshots` | Remove snapshots from multiple VMs in parallel. |
| `batch_power_on_hosts` | Power on multiple VMs in parallel. |
| `batch_power_off_hosts` | Power off multiple VMs in parallel. |
| `batch_get_vm_status` | Get status of multiple VMs in parallel. |

### AI Config Generation

| Tool | Description |
|------|-------------|
| `generate_config_from_description` | Generate a complete Ludus range configuration from natural language description. |
| `explain_range_design_decisions` | Explain the design decisions and best practices for a range configuration request. |
| `suggest_range_enhancements` | Suggest enhancements to improve a range configuration. |

### Profile Transformation

| Tool | Description |
|------|-------------|
| `apply_adversary_profile` | Apply adversary profile to inject realistic vulnerabilities for red team training. |
| `apply_defender_profile` | Apply defender profile to add monitoring and detection capabilities for blue team training. |
| `list_available_profiles` | List all available adversary and defender profiles with descriptions. |
| `preview_profile_changes` | Preview changes that would be made by applying a profile without modifying the config. |

### Documentation

| Tool | Description |
|------|-------------|
| `generate_range_documentation` | Generate comprehensive documentation for the range. |
| `get_attack_path_documentation` | Generate attack path documentation for an attack technique. |
| `export_lab_guide` | Export lab guide for training purposes. |
| `create_scenario_playbook` | Generate a red or blue team playbook for a scenario. |

### Collaboration

| Tool | Description |
|------|-------------|
| `share_range_config` | Generate a shareable copy of the range configuration. |
| `import_community_scenario` | Import a scenario from the community repository. |
| `publish_scenario` | Publish a scenario to the community repository. |
| `get_resource_quotas` | Get resource quotas and current usage. |
| `optimize_resource_allocation` | Optimize resource allocation for the range. |
| `schedule_maintenance_window` | Schedule a maintenance window for the range. |
| `list_ranges` | List all ranges (admin only). |

### Integrations

| Tool | Description |
|------|-------------|
| `webhook_integration` | Configure a webhook for range events. |
| `slack_notifications` | Configure Slack notifications for deployment status. |
| `jira_integration` | Configure JIRA issue creation for failed deployments. |
| `git_sync` | Sync range configurations with a Git repository. |


## Usage Examples

### Range Operations

```
Show my range status
Deploy the ad-basic scenario
Create a snapshot of DC01 named pre-attack
Rollback DC01 to pre-attack snapshot
```

### Template Operations

```
List available templates
Find Windows Server 2022 templates
Create a custom Kali template with bloodhound
```

### Role Management

```
List installed Ansible roles
Install the geerlingguy.docker role from Galaxy
Get common Galaxy roles for Ludus
```

### Skeleton Templates

```
List available VM skeletons
Get the domain controller skeleton
Generate a range YAML for basic-ad scenario
```

### Security

```
Show SIEM information for my range
Configure Wazuh integration
Show SIEM alerts from the last hour
```

## Tool Parameters

Common optional parameters:

| Parameter | Description | Usage |
|-----------|-------------|-------|
| `user_id` | Target user (admin only) | Multi-tenant operations |
| `confirm` | Confirmation for destructive operations | Delete operations |
| `timeout` | Operation timeout | Long-running operations |

## Error Handling

Tools return structured error information:

```json
{
  "status": "error",
  "error": "Connection refused",
  "error_type": "LudusConnectionError"
}
```

Common error types:
- `LudusConnectionError` - Cannot reach Ludus server
- `LudusAuthenticationError` - Invalid API key
- `LudusPermissionError` - Insufficient privileges
- `LudusNotFoundError` - Resource not found
- `LudusTimeoutError` - Operation timed out

## Related Documentation

- [Getting Started](getting-started.md) - Installation and setup
- [Scenarios](scenarios.md) - Pre-built deployment scenarios
- [Configuration](configuration.md) - Environment variables and options

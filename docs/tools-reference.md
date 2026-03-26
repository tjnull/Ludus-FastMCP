# Tools Reference

Complete reference for all tools available in Ludus FastMCP, organized by category.

## Overview

Ludus FastMCP provides tools across 20 modules. Tools marked with **(v2)** require a Ludus 2.0 server.

| Category | Tools | Description |
|----------|-------|-------------|
| Core Operations | 16 | Range, snapshot, power, network, template management |
| Deployment | 12 | Scenario deployment, orchestration, monitoring |
| User Management | 5 | User accounts, API keys, access control |
| Security Integration | 16 | SIEM configuration, compliance, vulnerability |
| Templates Advanced | 13 | Template discovery, creation, building |
| Metrics and Monitoring | 17 | Performance, health checks, inventory |
| Automation | 11 | Pipelines, scheduling, bulk operations |
| Integrations | 4 | Webhooks, Slack, Jira, Git |
| Documentation | 4 | Lab guides, attack paths, playbooks |
| Collaboration | 11 | Sharing, resources, community |
| Custom Builder | 18 | Skeleton templates, custom OS/containers |
| Range Management | 6 | List, search, delete, cleanup |
| AI Config Generation | 8 | Natural language to YAML |
| Profile Transformation | 5 | Adversary/defender profiles |
| Role Management | 11 | Ansible Galaxy, custom roles |
| Blueprints **(v2)** | ~13 | Blueprint lifecycle, sharing, access control |
| Groups **(v2)** | ~9 | Group management, membership, range access |
| VM Management **(v2)** | ~2 | VM destruction, console tickets |
| Diagnostics & Migration **(v2)** | ~7 | Diagnostics, license, SQLite/SDN migration |
| Enhanced Range Management **(v2)** | ~7 | Range creation, user assignment, defaults |

## Core Operations

Tools for managing ranges, snapshots, power states, hosts, networks, and templates.

### Range Management

| Tool | Description |
|------|-------------|
| `get_range` | Get current range information and status |
| `get_range_config` | Retrieve range configuration |
| `update_range_config` | Update range configuration |
| `deploy_range` | Deploy a range from configuration |
| `abort_range_deployment` | Stop an active deployment |
| `get_range_tags` | List available Ansible tags for deployment |
| `get_range_logs` | Retrieve deployment logs |
| `get_range_etchosts` | Get /etc/hosts file content |
| `get_range_sshconfig` | Get SSH configuration for range VMs |
| `get_range_rdpconfigs` | Get RDP configurations |
| `get_range_ansible_inventory` | Get Ansible inventory |

### Snapshot Operations

| Tool | Description |
|------|-------------|
| `snapshot_host` | Create a snapshot of a VM |
| `list_snapshots` | List all snapshots in the range |
| `rollback_snapshot` | Restore a VM to a snapshot |
| `remove_snapshot` | Delete a snapshot |

### Power Control

| Tool | Description |
|------|-------------|
| `power_on_range` | Power on all VMs in the range |
| `power_off_range` | Power off all VMs in the range |

## Deployment and Scenarios

Tools for deploying and managing pre-built scenarios.

### Scenario Deployment

| Tool | Description |
|------|-------------|
| `list_scenarios` | List available deployment scenarios |
| `preview_scenario` | Preview scenario configuration before deployment |
| `deploy_scenario` | Deploy a pre-built scenario |
| `smart_deploy` | Intelligent deployment with validation |

### Deployment Monitoring

| Tool | Description |
|------|-------------|
| `get_deployment_status` | Check current deployment status |
| `monitor_deployment` | Real-time deployment monitoring |
| `get_deployment_timeline` | Get deployment timeline and stages |
| `check_deployment_health` | Verify deployment health |

### Orchestration

| Tool | Description |
|------|-------------|
| `validate_config` | Validate range configuration |
| `recover_deployment` | Attempt to recover failed deployment |

## User Management

Tools for managing users and access control.

| Tool | Description |
|------|-------------|
| `list_users` | List all users (admin only) |
| `get_user` | Get user information |
| `add_user` | Create a new user (admin only) |
| `remove_user` | Delete a user (admin only) |
| `get_user_apikey` | Get or regenerate user API key |

## Security and SIEM

Tools for security monitoring and SIEM integration.

### SIEM Integration

| Tool | Description |
|------|-------------|
| `get_siem_info` | Get SIEM platform information |
| `configure_wazuh` | Configure Wazuh integration |
| `configure_splunk` | Configure Splunk integration |
| `configure_elastic` | Configure Elastic Stack integration |
| `configure_security_onion` | Configure Security Onion |
| `get_siem_alerts` | Retrieve SIEM alerts |

### Security Operations

| Tool | Description |
|------|-------------|
| `run_security_audit` | Execute security audit |
| `validate_compliance` | Check compliance against frameworks |
| `run_vulnerability_scan` | Execute vulnerability assessment |
| `get_detection_status` | Check detection tool status |

## Templates Advanced

Tools for advanced template management.

| Tool | Description |
|------|-------------|
| `discover_templates` | Search for templates by criteria |
| `get_template_info` | Get detailed template information |
| `get_template_status` | Check template build status |
| `get_template_logs` | Retrieve template operation logs |
| `build_template` | Build a template |
| `add_template` | Add a new template |
| `delete_template` | Remove a template |
| `abort_template_operation` | Cancel template operation |

## Custom Builder

Tools for creating custom templates, skeleton configurations, and ranges.

### Skeleton Templates

| Tool | Description |
|------|-------------|
| `list_vm_skeletons` | List available VM skeleton templates |
| `get_vm_skeleton` | Get a specific VM skeleton configuration |
| `list_range_skeletons` | List available range skeleton templates |
| `get_range_skeleton` | Get a complete range skeleton |
| `list_yaml_examples` | List available YAML configuration examples |
| `get_yaml_example` | Get a specific YAML example |
| `generate_range_yaml` | Generate range YAML from skeleton |
| `customize_skeleton` | Customize a skeleton template |

### Custom Templates

| Tool | Description |
|------|-------------|
| `create_custom_template` | Create custom OS template with packages |
| `create_container_template` | Create container-based template |
| `get_preconfigured_containers` | List available pre-configured containers |

### Custom Ranges

| Tool | Description |
|------|-------------|
| `build_custom_range` | Create range from scratch |
| `clone_scenario_with_modifications` | Clone and modify existing scenario |
| `export_range_config` | Export range configuration to YAML |

## Range Management

Tools for advanced range operations with safety features.

| Tool | Description |
|------|-------------|
| `list_all_ranges` | List all ranges with details |
| `list_ranges` | List ranges (simplified) |
| `get_user_range` | Get specific user's range |
| `find_range_by_vm` | Find range containing a specific VM |
| `delete_range` | Delete a range (with safety confirmation) |
| `delete_ranges_by_status` | Delete ranges by status (ERROR, FAILED) |

## Role Management

Tools for managing Ansible roles from Galaxy and custom repositories.

### Role Operations

| Tool | Description |
|------|-------------|
| `list_ansible_roles` | List installed Ansible roles |
| `get_role_details` | Get detailed role information |
| `install_ansible_role` | Install role via Ludus API |
| `remove_ansible_role` | Remove an installed role |
| `check_role_installed` | Check if a role is installed |

### Galaxy Integration

| Tool | Description |
|------|-------------|
| `install_galaxy_role` | Install role from Ansible Galaxy |
| `install_role_from_url` | Install role from Git repository |
| `get_common_galaxy_roles` | List commonly used Galaxy roles |
| `list_role_repositories` | List available role repositories |
| `get_roles_for_scenario` | Get recommended roles for a scenario |
| `get_roles_for_vm` | Get recommended roles for a VM type |

## AI Config Generation

Tools for generating configurations using natural language.

| Tool | Description |
|------|-------------|
| `generate_config_from_description` | Create config from natural language |
| `suggest_scenario` | Suggest appropriate scenario for use case |
| `optimize_config` | Optimize configuration for resources |
| `validate_and_fix_config` | Validate and auto-fix configuration issues |

## Profile Transformation

Tools for applying adversary and defender profiles.

| Tool | Description |
|------|-------------|
| `apply_redteam_profile` | Apply red team attack profile |
| `apply_blueteam_profile` | Apply blue team defense profile |
| `list_profiles` | List available profiles |
| `validate_profile` | Validate profile configuration |
| `get_profile_details` | Get detailed profile information |

## Metrics and Monitoring

Tools for performance and health monitoring.

| Tool | Description |
|------|-------------|
| `get_performance_metrics` | Retrieve performance metrics |
| `check_system_health` | Check overall system health |
| `get_inventory` | Get infrastructure inventory |
| `analyze_network_topology` | Analyze network configuration |
| `get_connectivity_status` | Check VM connectivity |
| `visualize_topology` | Generate network topology visualization |

## Automation

Tools for automation and bulk operations.

| Tool | Description |
|------|-------------|
| `create_deployment_pipeline` | Create automated deployment pipeline |
| `schedule_task` | Schedule a task for later execution |
| `run_bulk_operation` | Execute operation on multiple targets |
| `create_backup` | Create configuration backup |
| `restore_backup` | Restore from backup |

## Integrations

Tools for external service integration.

| Tool | Description |
|------|-------------|
| `configure_webhook` | Set up webhook notifications |
| `send_slack_notification` | Send message to Slack |
| `create_jira_ticket` | Create Jira ticket |
| `sync_git_config` | Sync configuration with Git repository |

## Documentation

Tools for generating documentation.

| Tool | Description |
|------|-------------|
| `generate_lab_guide` | Generate lab documentation |
| `generate_attack_path` | Document attack paths |
| `export_playbook` | Export as Ansible playbook |
| `generate_yaml_documentation` | Generate YAML config documentation |

## Collaboration

Tools for sharing and collaboration.

| Tool | Description |
|------|-------------|
| `share_range` | Share range with other users |
| `publish_scenario` | Publish scenario to community |
| `import_community_scenario` | Import community scenario |
| `list_shared_resources` | List shared resources |

## v2-Only Tools

The following tool categories are available only when connected to a Ludus v2 server. They are always visible in the tool list, but calling them against a v1 server will return an error indicating that Ludus v2 is required.

### Blueprints

Tools for managing range blueprints (v2 only).

| Tool | Description |
|------|-------------|
| `list_blueprints` | List all available blueprints |
| `create_blueprint_from_range` | Create a blueprint from an existing range |
| `apply_blueprint` | Apply a blueprint to create a new range |
| `copy_blueprint` | Copy an existing blueprint |
| `delete_blueprint` | Delete a blueprint |
| `get_blueprint_config` | Get blueprint configuration details |
| `update_blueprint_config` | Update blueprint configuration |
| `share_blueprint_with_user` | Share a blueprint with a specific user |
| `unshare_blueprint_with_user` | Revoke a user's access to a blueprint |
| `share_blueprint_with_group` | Share a blueprint with a group |
| `unshare_blueprint_with_group` | Revoke a group's access to a blueprint |
| `list_blueprint_access` | List users and groups with access to a blueprint |

### Groups

Tools for managing user groups (v2 only).

| Tool | Description |
|------|-------------|
| `list_groups` | List all groups |
| `create_group` | Create a new group |
| `delete_group` | Delete a group |
| `add_user_to_group` | Add a user to a group |
| `remove_user_from_group` | Remove a user from a group |
| `list_group_members` | List members of a group |
| `add_range_to_group` | Grant a group access to a range |
| `remove_range_from_group` | Revoke a group's access to a range |
| `list_group_ranges` | List ranges accessible by a group |

### VM Management

Additional VM lifecycle tools (v2 only).

| Tool | Description |
|------|-------------|
| `destroy_vm` | Permanently destroy a specific VM |
| `get_console_ticket` | Get a console access ticket for a VM |

### Diagnostics and Migration

Tools for server diagnostics and migration tasks (v2 only).

| Tool | Description |
|------|-------------|
| `run_diagnostics` | Run server diagnostics and return results |
| `whoami` | Return the currently authenticated user and server info |
| `get_license` | Get Ludus license information |
| `migrate_sqlite` | Run SQLite database migration |
| `get_sdn_migration_status` | Check status of SDN migration |
| `migrate_sdn` | Perform SDN migration |
| `setup_sdn` | Set up software-defined networking |

### Enhanced Range Management (v2)

Extended range tools available on v2 servers (v2 only).

| Tool | Description |
|------|-------------|
| `create_range` | Create a new empty range |
| `assign_user_to_range` | Assign a user to a range |
| `revoke_user_from_range` | Revoke a user's access to a range |
| `list_range_users` | List users assigned to a range |
| `list_accessible_ranges` | List all ranges the current user can access |
| `get_default_range` | Get the current user's default range |
| `set_default_range` | Set the current user's default range |

## Updated Tools in v2

The following existing tool categories have been enhanced when running against a v2 server.

### User Management Updates

- The `add_user` tool now accepts an optional `email` parameter.
- New support for OAuth2 provisioning for SSO-backed user creation.
- Users can query their group memberships via updated user info responses.

### Template Updates

- Roles can now be scoped to specific templates or ranges via a `role_scope` parameter.
- Role variables (`role_vars`) can be set per-template when assigning roles.
- Support for subscription-based roles that auto-update when the upstream source changes.

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

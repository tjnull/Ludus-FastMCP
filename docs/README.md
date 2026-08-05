# Ludus FastMCP Documentation

Documentation for Ludus FastMCP - MCP server for Ludus cyber range automation with 231 tools across 23 modules.

## Contents

### Getting Started

| Document | Description |
|----------|-------------|
| [Getting Started](getting-started.md) | Installation, setup, and first deployment |
| [Configuration](configuration.md) | Environment variables and MCP client setup |

### Reference

| Document | Description |
|----------|-------------|
| [Tools Reference](tools-reference.md) | Complete documentation for all 231 tools |
| [Scenarios](scenarios.md) | Pre-built deployment scenarios |

### Operations

| Document | Description |
|----------|-------------|
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |
| [Safety](safety.md) | Safety features and best practices |

## Quick Reference

### Installation

```bash
# Using pipx (recommended)
pipx install git+https://github.com/tjnull/ludus-mcp-python.git

# From source
git clone https://github.com/tjnull/ludus-mcp-python.git
cd ludus-mcp-python
pip install -e .
```

### Interactive Setup

Run the setup wizard to configure credentials and generate MCP client configurations:

```bash
ludus-fastmcp --setup
```

### Manual Configuration

```bash
export LUDUS_API_URL="https://your-ludus-instance:8080"
export LUDUS_API_KEY="username.your-api-key"
```

### Verify Installation

```bash
ludus-fastmcp --version
ludus-fastmcp --list-tools
```

### MCP Client Configuration

Configuration file locations:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ludus": {
      "command": "ludus-fastmcp",
      "env": {
        "LUDUS_API_URL": "https://your-ludus-instance:8080",
        "LUDUS_API_KEY": "username.your-api-key"
      }
    }
  }
}
```

### ludus-ai Client

```bash
ludus-ai setup-llm              # Configure local LLM (Ollama)
ludus-ai install anythingllm    # Install AnythingLLM interface
ludus-ai tool list-tools        # List available tools
ludus-ai tool call-tool <name>  # Execute tools directly
```

## Tool Categories

See the [Tools Reference](tools-reference.md) for every tool by name.

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

## External Resources

| Resource | Link |
|----------|------|
| Ludus Documentation | [docs.ludus.cloud](https://docs.ludus.cloud) |
| Ludus GitHub | [github.com/badsectorlabs/ludus](https://github.com/badsectorlabs/ludus) |
| FastMCP Framework | [gofastmcp.com](https://gofastmcp.com) |
| MCP Protocol | [modelcontextprotocol.io](https://modelcontextprotocol.io) |

## Support

| Resource | Link |
|----------|------|
| GitHub Issues | [github.com/tjnull/ludus-mcp-python/issues](https://github.com/tjnull/ludus-mcp-python/issues) |
| GitHub Discussions | [github.com/tjnull/ludus-mcp-python/discussions](https://github.com/tjnull/ludus-mcp-python/discussions) |

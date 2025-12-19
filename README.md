# Ludus FastMCP

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/tjnull/ludus-mcp-python)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

A Model Context Protocol (MCP) server for automating [Ludus](https://docs.ludus.cloud) cyber range environments through AI assistants written in Python.

## Overview

Ludus FastMCP enables AI-powered management of Ludus cyber ranges through natural language commands. The server exposes **157 tools** across 15 modules for range lifecycle management, scenario deployment, template creation, Ansible role management, and security monitoring integration.

### Key Capabilities

| Category | Description |
|----------|-------------|
| **Range Management** | Create, configure, deploy, and manage virtual lab environments |
| **Scenario Deployment** | Pre-built scenarios for AD, red/blue/purple team, and malware analysis |
| **Template Builder** | Custom OS templates, skeleton configurations, and YAML generation |
| **Role Management** | Ansible Galaxy integration and custom role installation |
| **SIEM Integration** | Wazuh, Splunk, Elastic Stack, and Security Onion support |
| **AI Configuration** | Natural language to YAML configuration conversion |

### Supported Platforms

Works with any MCP-compatible client including Claude Desktop, VS Code (Cline), OpenWebUI, and AnythingLLM.

## Quick Start

### Requirements

- Python 3.11+
- Access to a Ludus server instance
- Ludus API credentials

### Installation

```bash
# Using pipx (recommended)
pipx install git+https://github.com/tjnull/Ludus-FastMCP

# From source
git clone https://github.com/tjnull/Ludus-FastMCP
cd Ludus-FastMCP
pip install -e .
```

### Setup

Run the interactive setup wizard:

```bash
ludus-fastmcp --setup
```

The wizard configures API credentials, tests connectivity, and generates MCP client configuration files.

For manual configuration options, see the [Configuration Guide](docs/configuration.md).

## Usage

### MCP Server (ludus-fastmcp)

```bash
ludus-fastmcp --setup          # Interactive setup wizard
ludus-fastmcp --list-tools     # List all 157 available tools
ludus-fastmcp --version        # Display version information
ludus-fastmcp                  # Start MCP server
ludus-fastmcp --daemon         # Run as background service
```

### Client CLI (ludus-ai)

```bash
ludus-ai setup-llm                    # Configure local LLM (Ollama)
ludus-ai install anythingllm          # Install AnythingLLM interface
ludus-ai tool list-tools              # List available tools
ludus-ai tool call-tool <name>        # Execute tools directly
```

### Example Interactions

Once connected to an MCP client, interact with your Ludus environment:

```
Show my current range status
Deploy an Active Directory lab with Wazuh monitoring
Create a snapshot named "pre-attack" for all VMs
Build a lab with 2 domain controllers and 5 workstations
```

Examples of using Ludus-FastMCP with grok code through Opencode.

![img](docs/images/health-check.png)

![img](docs/images/scenarios.png)

![img](docs/images/templates.png)

![img](docs/images/range-check.png)

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, setup, and first deployment |
| [Configuration](docs/configuration.md) | Environment variables and MCP client setup |
| [Tools Reference](docs/tools-reference.md) | Complete documentation for all 157 tools |
| [Scenarios](docs/scenarios.md) | Pre-built deployment scenarios |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and solutions |
| [Safety](docs/safety.md) | Safety features and best practices |

## Resources

| Resource | Link |
|----------|------|
| Ludus Documentation | [docs.ludus.cloud](https://docs.ludus.cloud) |
| Ludus GitHub | [github.com/badsectorlabs/ludus](https://github.com/badsectorlabs/ludus) |
| FastMCP Framework | [gofastmcp.com](https://gofastmcp.com) |
| MCP Specification | [modelcontextprotocol.io](https://modelcontextprotocol.io) |

## Support

- [GitHub Issues](https://github.com/tjnull/ludus-mcp-python/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/tjnull/ludus-mcp-python/discussions) - Questions and community discussion

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer

This software is intended for authorized security testing, educational purposes, and research in controlled environments. Users are responsible for compliance with applicable laws and organizational policies. The authors make no warranties and assume no liability for use or misuse of this software.

## Acknowledgments

- [Ludus](https://github.com/badsectorlabs/ludus) by Bad Sector Labs
- [FastMCP](https://gofastmcp.com), and the Model Context Protocol community.

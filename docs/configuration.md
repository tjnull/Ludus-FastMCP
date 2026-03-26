# Configuration

Complete configuration reference for Ludus FastMCP, including environment variables, MCP client setup, and advanced options.

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `LUDUS_API_URL` | Ludus server URL | `https://ludus.example.com:8080` |
| `LUDUS_API_KEY` | API authentication key | `username.abc123def456` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `LUDUS_API_VERSION` | `auto` | API version selection: `auto` (default), `v1`, or `v2`. Auto-detects the server version on first API call. |
| `LUDUS_JWT_TOKEN` | — | JWT Bearer token for Pro/SSO users. When set, takes precedence over `LUDUS_API_KEY`. |
| `LUDUS_SSL_VERIFY` | `false` | Enable SSL certificate verification |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |

### SSH Role Installation (Optional)

For automatic Ansible role installation from Git repositories:

| Variable | Description |
|----------|-------------|
| `LUDUS_SSH_HOST` | Ludus server SSH hostname |
| `LUDUS_SSH_USER` | SSH username |
| `LUDUS_SSH_KEY_PATH` | Path to SSH private key |
| `LUDUS_SSH_PASSWORD` | SSH password (if not using key) |
| `LUDUS_ALLOW_SSH_INSTALL` | Set to `true` to enable SSH-based role installation |

## Configuration Methods

### Method 1: Interactive Setup (Recommended)

```bash
ludus-fastmcp --setup
```

The setup wizard configures all required settings interactively.

### Method 2: Environment File

Create a `.env` file in your working directory:

```bash
LUDUS_API_URL=https://your-ludus-instance:8080
LUDUS_API_KEY=username.your-api-key
LUDUS_SSL_VERIFY=false
LOG_LEVEL=INFO
```

### Method 3: Shell Export

```bash
export LUDUS_API_URL="https://your-ludus-instance:8080"
export LUDUS_API_KEY="username.your-api-key"
```

### Method 4: MCP Client Configuration

Environment variables can be set directly in your MCP client's configuration file. This approach keeps credentials isolated per client.

## MCP Client Configuration

For detailed setup instructions for each client, see [Getting Started](getting-started.md#mcp-client-configuration).

### Using Full Path

If your MCP client cannot locate `ludus-fastmcp`, use the full path:

```json
{
  "mcpServers": {
    "ludus": {
      "command": "/home/username/.local/bin/ludus-fastmcp",
      "env": {
        "LUDUS_API_URL": "https://your-ludus-instance:8080",
        "LUDUS_API_KEY": "username.your-api-key"
      }
    }
  }
}
```

Find your installation path:

```bash
which ludus-fastmcp
```

## Multiple Ludus Servers

Connect to multiple Ludus instances by creating separate MCP server entries:

```json
{
  "mcpServers": {
    "ludus-prod": {
      "command": "ludus-fastmcp",
      "env": {
        "LUDUS_API_URL": "https://prod.ludus.example.com:8080",
        "LUDUS_API_KEY": "produser.api-key"
      }
    },
    "ludus-dev": {
      "command": "ludus-fastmcp",
      "env": {
        "LUDUS_API_URL": "https://dev.ludus.example.com:8080",
        "LUDUS_API_KEY": "devuser.api-key"
      }
    }
  }
}
```

Specify which server to use in commands:
- "Using ludus-prod, show my ranges"
- "Using ludus-dev, deploy ad-basic"

## SSL Configuration

### Self-Signed Certificates

Most Ludus installations use self-signed certificates. SSL verification is disabled by default:

```bash
LUDUS_SSL_VERIFY=false
```

### Valid Certificates

For production environments with valid SSL certificates:

```bash
LUDUS_SSL_VERIFY=true
```

## Server Operation Modes

### Foreground Mode (Default)

Standard MCP server operation:

```bash
ludus-fastmcp
```

### Verbose Mode

Display detailed logging during operation:

```bash
ludus-fastmcp --verbose
```

### Daemon Mode

Run as a background service:

```bash
ludus-fastmcp --daemon          # Start
ludus-fastmcp --status          # Check status
ludus-fastmcp --stop-daemon     # Stop
```

Daemon files:
- PID file: `~/.ludus-fastmcp/ludus-fastmcp.pid`
- Log file: `~/.ludus-fastmcp/ludus-fastmcp.log`

## Logging

### Log Levels

| Level | Description |
|-------|-------------|
| `DEBUG` | Detailed debugging information |
| `INFO` | General operational messages |
| `WARNING` | Warning messages |
| `ERROR` | Error messages only |

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
ludus-fastmcp --verbose
```

### View Logs

```bash
# Daemon logs
tail -f ~/.ludus-fastmcp/ludus-fastmcp.log

# Filter errors
grep ERROR ~/.ludus-fastmcp/ludus-fastmcp.log
```

## API Key Management

### Retrieve Key

On your Ludus server:

```bash
ludus user apikey
```

### Key Format

Keys follow the format: `username.key-value`

Example: `admin.a1b2c3d4e5f6g7h8`

### Security Practices

- Store keys in environment variables or MCP client configuration
- Do not commit keys to version control
- Add `.env` to `.gitignore`
- Rotate keys periodically via Ludus CLI
- Use separate keys for development and production

## Verification

### Test Configuration

```bash
# Verify environment variables
echo $LUDUS_API_URL
echo $LUDUS_API_KEY

# Test server startup
ludus-fastmcp --verbose

# List tools (confirms installation)
ludus-fastmcp --list-tools
```

### Test Connectivity

```bash
# Test Ludus API directly
curl -k -H "X-API-KEY: $LUDUS_API_KEY" $LUDUS_API_URL/

# Expected: JSON response with server info
```

### Test MCP Integration

After configuring your MCP client:

```
List all available Ludus tools
```

Successful response displays 157 tools organized by category.

## ludus-ai Client Configuration

The `ludus-ai` CLI provides additional functionality:

### Local LLM Setup

```bash
ludus-ai setup-llm
```

Configures Ollama for local LLM support.

### Chat Interface Installation

```bash
ludus-ai install anythingllm    # Recommended
ludus-ai install openwebui
ludus-ai install opencode
```

### Cache Management

```bash
ludus-ai clear-cache --all
ludus-ai clear-cache --opencode
```

## Ludus 2.0 Support

Ludus FastMCP supports both Ludus v1 and v2 servers. This section covers what changes with v2 and how to configure the server accordingly.

### Auto-Detection

By default (`LUDUS_API_VERSION=auto`), the server automatically detects whether it is connected to a v1 or v2 Ludus instance on the first API call. No manual configuration is needed in most cases.

### Overriding the API Version

If you want to skip auto-detection and target a specific version, set the environment variable explicitly:

```bash
export LUDUS_API_VERSION=v2
```

This can be useful in CI/CD pipelines or when connecting to a known v2 server to avoid the initial detection round-trip.

### Backwards Compatibility

All existing tools continue to work on v1 servers without any changes. Upgrading Ludus FastMCP does not break existing v1 workflows.

### v2-Only Tools

Ludus 2.0 introduces new tool categories (Blueprints, Groups, VM Management, Diagnostics & Migration, and enhanced Range Management). These tools are always visible regardless of the detected server version, but calling them against a v1 server will return a clear error message indicating that the tool requires Ludus v2.

See the [Tools Reference](tools-reference.md) for the full list of v2-only tools.

### JWT Authentication (Pro / SSO)

For Ludus Pro users authenticating via SSO, set `LUDUS_JWT_TOKEN` instead of `LUDUS_API_KEY`:

```bash
export LUDUS_JWT_TOKEN="eyJhbGciOiJSUzI1NiIs..."
```

When `LUDUS_JWT_TOKEN` is set it takes precedence over `LUDUS_API_KEY`. The token is sent as a standard `Authorization: Bearer <token>` header.

Example MCP client configuration with JWT:

```json
{
  "mcpServers": {
    "ludus": {
      "command": "ludus-fastmcp",
      "env": {
        "LUDUS_API_URL": "https://your-ludus-instance:8080",
        "LUDUS_JWT_TOKEN": "eyJhbGciOiJSUzI1NiIs..."
      }
    }
  }
}
```

## Related Documentation

- [Getting Started](getting-started.md) - Installation and initial setup
- [Tools Reference](tools-reference.md) - Complete tool documentation
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

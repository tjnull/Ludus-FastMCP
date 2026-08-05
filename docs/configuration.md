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
| `LUDUS_API_VERSION` | `auto` | `auto` (default) verifies the server is Ludus 2.x on the first call; `v2` asserts it and skips that check. `v1` is rejected -- this release is Ludus 2.x only. |
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

Successful response displays 231 tools organized by category.

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

## Ludus Server Version

This release speaks the Ludus 2.x API only. Every request goes to `/api/v2`.

### Verification

By default (`LUDUS_API_VERSION=auto`) the client asks the server for its version
on the first call and refuses to continue if the answer is not a 2.x server:

```
https://ludus.example:8080 does not serve the Ludus 2.x API
(GET /api/v2/ returned HTTP 404). This release requires Ludus 2.0 or later;
upgrade the server, or pin ludus-fastmcp to a 1.x release for a Ludus 1.x server.
```

Checking once, up front, means a version mismatch is reported plainly rather
than appearing as an unexplained 404 from whichever tool ran first.

### Skipping the check

If you already know the server is 2.x, assert it and save the round-trip:

```bash
export LUDUS_API_VERSION=v2
```

Useful in CI, or anywhere you would rather not spend a request per session.

### Ludus 1.x servers

`LUDUS_API_VERSION=v1` is rejected at startup rather than silently ignored:

```
LUDUS_API_VERSION=v1 is no longer supported. This release targets the Ludus 2.x
API only. Upgrade your Ludus server to 2.0 or later, or pin ludus-fastmcp to a
1.x release for a v1 server.
```

Blueprints, content sources, groups, quotas, deployment log history and VM
console access have no equivalent in the 1.x API, so upgrading the server is the
better path.

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

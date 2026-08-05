# Getting Started

This guide covers installation, configuration, and initial deployment with Ludus FastMCP.

## Prerequisites

### Required

| Requirement | Description |
|-------------|-------------|
| Python 3.11+ | `python --version` to verify |
| Ludus Server | Running Ludus instance with network access |
| API Credentials | Generate with `ludus user apikey` on server |

### Optional (Recommended)

| Component | Description |
|-----------|-------------|
| MCP Client | Claude Desktop, VS Code (Cline), AnythingLLM, or OpenWebUI |
| pipx | Isolated Python application management |

## Installation

### Method 1: Using pipx (Recommended)

pipx installs applications in isolated environments while making them globally available.

```bash
# Install pipx if not present
pip install pipx
pipx ensurepath

# Install Ludus FastMCP
pipx install git+https://github.com/tjnull/ludus-mcp-python.git
```

### Method 2: From Source

```bash
git clone https://github.com/tjnull/ludus-mcp-python.git
cd ludus-mcp-python

python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -e .
```

### Verify Installation

```bash
ludus-fastmcp --version
ludus-fastmcp --list-tools  # Should display 231 tools
```

## Configuration

### Interactive Setup (Recommended)

Run the setup wizard to configure all prerequisites:

```bash
ludus-fastmcp --setup
```

The wizard will:
- Verify Python environment and dependencies
- Configure Ludus API credentials
- Test connectivity to your Ludus server
- Generate MCP client configuration files

### Manual Configuration

#### Environment Variables

Create a `.env` file in your working directory:

```bash
LUDUS_API_URL=https://your-ludus-instance:8080
LUDUS_API_KEY=username.your-api-key
```

Or export directly:

```bash
export LUDUS_API_URL="https://your-ludus-instance:8080"
export LUDUS_API_KEY="username.your-api-key"
```

#### Test Connection

```bash
ludus-fastmcp --verbose
```

Successful output:

```
[INFO] Server Configuration:
  API URL: https://your-ludus-instance:8080
  API Key: ********************...
```

Press Ctrl+C to stop the test server.

## MCP Client Configuration

### Claude Desktop

1. Locate configuration file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. Add server configuration:

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

3. Restart Claude Desktop (quit and reopen, not just close window)

4. Verify: Ask Claude "List my Ludus ranges"

### VS Code with Cline

1. Install Cline extension from VS Code marketplace

2. Open Settings (Cmd+, or Ctrl+,)

3. Search for "Cline MCP Servers"

4. Edit settings.json:

```json
{
  "cline.mcpServers": {
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

5. Reload VS Code (Cmd+Shift+P > "Developer: Reload Window")

### AnythingLLM

1. Navigate to Settings > Agent Configuration > Agent Skills

2. Scroll to MCP Servers and click Add new MCP Server

3. Configure:
   - Transport Type: `stdio`
   - Name: `ludus`
   - Command: `ludus-fastmcp`

4. Add environment variables:
   ```
   LUDUS_API_URL=https://your-ludus-instance:8080
   LUDUS_API_KEY=username.your-api-key
   ```

5. Save and enable the MCP server

### OpenWebUI

1. Navigate to Admin Panel > Settings > Tools

2. Click Add MCP Server:

```json
{
  "name": "ludus",
  "transport": "stdio",
  "command": "ludus-fastmcp",
  "env": {
    "LUDUS_API_URL": "https://your-ludus-instance:8080",
    "LUDUS_API_KEY": "username.your-api-key"
  }
}
```

3. Save and refresh

### OpenCode

1. Edit `~/.config/opencode/config.json`:

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

2. Alternatively, use CLI:

```bash
opencode mcp add ludus --command "ludus-fastmcp" \
  --env "LUDUS_API_URL=https://your-ludus-instance:8080" \
  --env "LUDUS_API_KEY=username.your-api-key"
```

3. Restart OpenCode

## First Deployment

Once connected to your MCP client:

### Check Status

```
Show my current range status
```

### List Templates

```
List all available Ludus templates
```

### Deploy Scenario

```
Deploy the ad-basic scenario
```

This deploys a basic Active Directory environment:
- 1 Domain Controller (Windows Server)
- 1 Workstation (Windows 10/11)

Deployment time: 15-45 minutes depending on scenario complexity.

### Monitor Deployment

```
Show deployment status
```

### Create Snapshot

After deployment completes:

```
Create a snapshot of all VMs named clean-state
```

## Command Line Usage

### ludus-fastmcp Commands

```bash
ludus-fastmcp --setup           # Interactive setup wizard
ludus-fastmcp --setup-guide     # Manual setup instructions
ludus-fastmcp --list-tools      # List all 231 tools
ludus-fastmcp --version         # Version information
ludus-fastmcp --verbose         # Start with verbose logging
ludus-fastmcp --daemon          # Run as background service
ludus-fastmcp --status          # Check daemon status
ludus-fastmcp --stop-daemon     # Stop daemon
```

### ludus-ai Commands

```bash
ludus-ai --help                 # Show available commands
ludus-ai setup-llm              # Configure local LLM (Ollama)
ludus-ai install anythingllm    # Install AnythingLLM
ludus-ai tool list-tools        # List tools via MCP
ludus-ai tool list-ranges       # List ranges
ludus-ai tool call-tool <name>  # Execute tool directly
```

## Next Steps

- [Configuration Guide](configuration.md) - Advanced configuration options
- [Tools Reference](tools-reference.md) - Complete tool documentation (231 tools)
- [Scenarios Guide](scenarios.md) - Available deployment scenarios
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

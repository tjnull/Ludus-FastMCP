"""FastMCP server entry point for Ludus MCP."""

import sys
import os
import asyncio
import signal
import atexit
from pathlib import Path
from datetime import datetime
from fastmcp import FastMCP
from ludus_mcp.core.client import LudusAPIClient
from ludus_mcp.server.tools.core import create_core_tools
from ludus_mcp.utils.config import get_settings
from ludus_mcp.utils.logging import setup_logging, get_logger

# Global flags
_verbose_mode = False
_daemon_mode = False

# Setup logging (quiet mode by default for MCP server)
setup_logging(quiet=True)
logger = get_logger(__name__)

# Global client (lazy initialization)
_client: LudusAPIClient | None = None
_client_initialized = False

# Global MCP server (lazy initialization)
_mcp: FastMCP | None = None


def get_client() -> LudusAPIClient:
    """Get or create the Ludus API client.

    Returns:
        LudusAPIClient instance
    """
    global _client, _client_initialized
    if _client is None:
        settings = get_settings()

        # Validate configuration
        if not settings.ludus_api_url:
            raise RuntimeError(
                "LUDUS_API_URL is not set. Please configure it in your .env file or environment."
            )
        if not settings.ludus_api_key:
            raise RuntimeError(
                "LUDUS_API_KEY is not set. Please configure it in your .env file or environment."
            )

        _client = LudusAPIClient()

        # Log initialization (only once)
        if not _client_initialized:
            if _verbose_mode:
                _print_startup_banner(settings)
            _client_initialized = True

    return _client


def _print_startup_banner(settings):
    """Print enhanced startup banner with logging."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "╔" + "═" * 78 + "╗", file=sys.stderr)
    print("║" + " " * 78 + "║", file=sys.stderr)
    print("║" + "  Ludus MCP Server (FastMCP)".center(78) + "║", file=sys.stderr)
    print("║" + f"  Version 1.0 - {timestamp}".center(78) + "║", file=sys.stderr)
    print("║" + " " * 78 + "║", file=sys.stderr)
    print("╚" + "═" * 78 + "╝", file=sys.stderr)
    print(file=sys.stderr)
    print("[INFO] Server Configuration:", file=sys.stderr)
    print(f"  • API URL:     {settings.ludus_api_url}", file=sys.stderr)
    print(f"  • API Key:     {'*' * 20}...{settings.ludus_api_key[-8:] if settings.ludus_api_key else 'Not set'}", file=sys.stderr)
    print(f"  • Log Level:   {'VERBOSE' if _verbose_mode else 'QUIET'}", file=sys.stderr)
    print(f"  • Mode:        {'DAEMON' if _daemon_mode else 'FOREGROUND'}", file=sys.stderr)
    print(file=sys.stderr)


def _initialize_mcp_server() -> FastMCP:
    """Initialize the MCP server with all tools.

    This is called lazily to avoid requiring API credentials for --help, --setup, etc.
    """
    global _mcp

    if _mcp is not None:
        return _mcp

    # Create main FastMCP server and register tools
    client = get_client()
    mcp = create_core_tools(client)

    # Import all tool modules
    try:
        from ludus_mcp.server.tools.deployment import create_deployment_tools
        from ludus_mcp.server.tools.users import create_user_tools
        from ludus_mcp.server.tools.security import create_security_tools
        from ludus_mcp.server.tools.templates_advanced import create_template_advanced_tools
        from ludus_mcp.server.tools.metrics import create_metrics_tools
        from ludus_mcp.server.tools.automation import create_automation_tools
        from ludus_mcp.server.tools.integrations import create_integration_tools
        from ludus_mcp.server.tools.documentation import create_documentation_tools
        from ludus_mcp.server.tools.collaboration import create_collaboration_tools
        from ludus_mcp.server.tools.batch import create_batch_tools
        from ludus_mcp.server.tools.custom_builder import create_custom_builder_tools
        from ludus_mcp.server.tools.range_management import create_range_management_tools
        from ludus_mcp.server.tools.ai_generation import create_ai_config_tools
        from ludus_mcp.server.tools.profile_transformation import create_profile_transformation_tools
        from ludus_mcp.server.tools.role_management import create_role_management_tools

        # Import all tool servers into main server
        tool_modules = [
            ("Deployment", create_deployment_tools),
            ("Users", create_user_tools),
            ("Security", create_security_tools),
            ("Templates Advanced", create_template_advanced_tools),
            ("Metrics", create_metrics_tools),
            ("Automation", create_automation_tools),
            ("Integrations", create_integration_tools),
            ("Documentation", create_documentation_tools),
            ("Collaboration", create_collaboration_tools),
            ("Batch Operations", create_batch_tools),
            ("Custom Template & Range Builder", create_custom_builder_tools),
            ("Range Management", create_range_management_tools),
            ("AI Configuration Generation", create_ai_config_tools),
            ("Adversary/Defender Profiles", create_profile_transformation_tools),
            ("Role Management", create_role_management_tools),
        ]

        if _verbose_mode:
            print("[INFO] Loading Tool Modules:", file=sys.stderr)

        loaded_modules = []
        failed_modules = []

        for module_name, create_func in tool_modules:
            try:
                if _verbose_mode:
                    print(f"  ⏳ Loading {module_name}...", end="", file=sys.stderr, flush=True)

                module_server = create_func(client)

                # Use mount() instead of asyncio.run(mcp.import_server()) to avoid event loop conflicts.
                # When called from async contexts (e.g., --list-tools runs via asyncio.run(list_tools_async())),
                # attempting to create a new event loop with asyncio.run() fails because an event loop is
                # already running in the current thread. mount() performs synchronous tool registration without
                # requiring a new event loop, making it safe to call from both sync and async contexts.
                mcp.mount(module_server)
                loaded_modules.append(module_name)

                if _verbose_mode:
                    print(f" [OK]", file=sys.stderr)

                logger.info(f"{module_name} tools loaded successfully")
            except Exception as e:
                failed_modules.append((module_name, str(e)))

                if _verbose_mode:
                    print(f" [ERROR] ({e})", file=sys.stderr)

                logger.warning(f"Could not load {module_name} tools: {e}")

        if _verbose_mode:
            print(file=sys.stderr)
            print(f"[OK] Successfully loaded {len(loaded_modules)}/{len(tool_modules)} modules", file=sys.stderr)
            if failed_modules:
                print(f"[WARNING] Failed to load {len(failed_modules)} modules:", file=sys.stderr)
                for name, error in failed_modules:
                    print(f"  • {name}: {error}", file=sys.stderr)
            print(file=sys.stderr)

    except Exception as e:
        logger.error(f"Error loading tool modules: {e}")
        if _verbose_mode:
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"ERROR: Failed to load tool modules: {e}", file=sys.stderr)
            print("Run with --verbose for more details", file=sys.stderr)
        raise

    _mcp = mcp
    return mcp


def print_help():
    """Print help information about ludus-fastmcp."""
    help_text = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        Ludus FastMCP Server                                  ║
║                              Version 1.0                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

USAGE:
    ludus-fastmcp [OPTIONS]

OPTIONS:
    --help, -h              Show this help message
    --list-tools, -l        List all 157 available FastMCP tools
    --list-tools-detailed   List tools with descriptions
    --version, -v           Show version information (v1.0)
    --setup                 Run interactive setup wizard (configure API, LLM, etc.)
    --setup-guide           Show manual setup instructions
    --verbose, -V           Enable verbose logging (shows module loading, etc.)
    --daemon, -d            Run in daemon/background mode
    --stop-daemon           Stop the daemon process
    --status                Check daemon status and view logs

DESCRIPTION:
    Ludus FastMCP Server provides Model Context Protocol (MCP) integration for
    Ludus, enabling AI assistants to manage cybersecurity lab environments.

    Version 1.0 includes 157 tools across 15 modules with skeleton templates,
    Ansible Galaxy role management, and enhanced AI-assisted range building.

SETUP:
    1. Configure environment variables:
       export LUDUS_API_URL="https://your-ludus-instance:8080"
       export LUDUS_API_KEY="your-api-key"

    2. Or create a .env file in the project root:
       LUDUS_API_URL=https://your-ludus-instance:8080
       LUDUS_API_KEY=your-api-key

    3. Run the server:
       ludus-fastmcp

MCP CLIENT CONFIGURATION:
    Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "ludus": {
          "command": "/path/to/.venv/bin/ludus-fastmcp",
          "env": {
            "LUDUS_API_URL": "https://your-ludus-instance:8080",
            "LUDUS_API_KEY": "your-api-key"
          }
        }
      }
    }

    VS Code (settings.json):
    {
      "cline.mcpServers": {
        "ludus": {
          "command": "/path/to/.venv/bin/ludus-fastmcp",
          "env": {
            "LUDUS_API_URL": "https://your-ludus-instance:8080",
            "LUDUS_API_KEY": "your-api-key"
          }
        }
      }
    }

AVAILABLE TOOL CATEGORIES (157 tools total):
    • Core Operations (16 tools)        - Ranges, snapshots, power, templates
    • Deployment (12 tools)             - Scenarios, orchestration, monitoring
    • Users (5 tools)                   - User management
    • Security & SIEM (16 tools)        - Security monitoring, compliance
    • Templates Advanced (13 tools)     - Template management & building
    • Metrics & Monitoring (17 tools)   - Metrics, inventory, network analysis
    • Automation (11 tools)             - Pipelines, backups, bulk operations
    • Integrations (4 tools)            - Webhooks, Slack, Jira, Git
    • Documentation (4 tools)           - Generate docs, lab guides
    • Collaboration (11 tools)          - Sharing, resources, community
    • Custom Builder (18 tools)         - Skeleton templates, YAML examples
    • Range Management (6 tools)        - Selective VM management
    • AI Config Generation (8 tools)    - Natural language config building
    • Profile Transformation (5 tools)  - Adversary/defender profiles
    • Role Management (11 tools)        - Ansible Galaxy & custom roles

DOCUMENTATION:
    GitHub: https://github.com/badsectorlabs/ludus
    Docs:   https://docs.ludus.cloud

For more information, run: ludus-fastmcp --list-tools
"""
    print(help_text)


async def list_tools_async(detailed: bool = False):
    """List all available tools."""
    mcp = _initialize_mcp_server()
    tools = await mcp.get_tools()

    print("\n" + "=" * 80)
    print(f"Ludus MCP Tools - {len(tools)} tools available")
    print("=" * 80 + "\n")

    # Categorize tools
    categories = {
        "Core Operations": [],
        "Deployment & Scenarios": [],
        "Users & Access": [],
        "Security & SIEM": [],
        "Templates": [],
        "Metrics & Monitoring": [],
        "Automation & Orchestration": [],
        "Integrations": [],
        "Documentation": [],
        "Collaboration & Resources": [],
        "Other": []
    }

    for tool in sorted(tools):
        # Categorize based on tool name
        if any(x in tool for x in ["range", "snapshot", "power", "host", "network", "testing"]):
            categories["Core Operations"].append(tool)
        elif any(x in tool for x in ["deploy", "scenario", "monitor", "timeline", "status"]):
            categories["Deployment & Scenarios"].append(tool)
        elif any(x in tool for x in ["user", "access", "grant", "revoke"]):
            categories["Users & Access"].append(tool)
        elif any(x in tool for x in ["siem", "wazuh", "security", "compliance", "vulnerability", "detection"]):
            categories["Security & SIEM"].append(tool)
        elif any(x in tool for x in ["template", "container"]):
            categories["Templates"].append(tool)
        elif any(x in tool for x in ["metric", "inventory", "network", "health", "visualize", "ansible", "ssh", "rdp", "etchosts", "topology", "connectivity"]):
            categories["Metrics & Monitoring"].append(tool)
        elif any(x in tool for x in ["pipeline", "schedule", "scaling", "bulk", "recovery", "clone", "backup", "export", "import"]):
            categories["Automation & Orchestration"].append(tool)
        elif any(x in tool for x in ["webhook", "slack", "jira", "git"]):
            categories["Integrations"].append(tool)
        elif any(x in tool for x in ["documentation", "attack_path", "lab_guide", "playbook", "yaml"]):
            categories["Documentation"].append(tool)
        elif any(x in tool for x in ["share", "publish", "community", "interactive", "build_range", "list_ranges", "resource", "maintenance"]):
            categories["Collaboration & Resources"].append(tool)
        else:
            categories["Other"].append(tool)

    # Print categorized tools
    for category, tool_list in categories.items():
        if tool_list:
            print(f"\n{category} ({len(tool_list)} tools):")
            print("-" * 80)
            for tool in sorted(tool_list):
                if detailed:
                    # TODO: Get tool description from FastMCP if available
                    print(f"  • {tool}")
                else:
                    print(f"  • {tool}")

    print("\n" + "=" * 80)
    print(f"Total: {len(tools)} tools")
    print("=" * 80 + "\n")


def print_version():
    """Print version information."""
    print("""
Ludus FastMCP Server
Version: 1.0
FastMCP: 2.2.0+
Python: 3.11+

Features (v1.0):
  - 157 FastMCP tools across 15 modules
  - Skeleton Templates (8 tools) - Pre-built VM and range configurations
  - Role Management (11 tools) - Ansible Galaxy & custom role installation
  - Custom Template Builder (18 tools) - Create custom OS/container templates
  - Range Management (6 tools) - Selective range deletion with safety
  - AI Config Generation - Natural language to YAML configs
  - Enhanced Logging - Verbose mode with module loading progress
  - Daemon Mode - Background operation with status monitoring
  - FastMCP-based architecture
  - Async/await support

Built with FastMCP: https://gofastmcp.com
""")


def print_setup():
    """Print setup instructions."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        Ludus MCP Setup Guide                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

STEP 1: Install Dependencies
─────────────────────────────────────────────────────────────────────────────────
    cd /path/to/LudusMCP-Python
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
    pip install -e .

STEP 2: Configure Ludus API
─────────────────────────────────────────────────────────────────────────────────
    Option A - Environment Variables:
        export LUDUS_API_URL="https://your-ludus-instance:8080"
        export LUDUS_API_KEY="your-api-key"

    Option B - .env File (recommended):
        Create .env file in project root:

        LUDUS_API_URL=https://your-ludus-instance:8080
        LUDUS_API_KEY=your-api-key

    Get your Ludus API key from:
        ludus user apikey

STEP 3: Test the Server
─────────────────────────────────────────────────────────────────────────────────
    # List available tools
    ludus-fastmcp --list-tools

    # Start the server (for MCP clients)
    ludus-fastmcp

STEP 4: Configure MCP Client
─────────────────────────────────────────────────────────────────────────────────
    Claude Desktop:
        Location: ~/Library/Application Support/Claude/claude_desktop_config.json
        Or: %APPDATA%\\Claude\\claude_desktop_config.json (Windows)

        {
          "mcpServers": {
            "ludus": {
              "command": "/absolute/path/to/.venv/bin/ludus-fastmcp",
              "env": {
                "LUDUS_API_URL": "https://your-ludus-instance:8080",
                "LUDUS_API_KEY": "your-api-key"
              }
            }
          }
        }

    VS Code (Cline extension):
        Location: Settings → Extensions → Cline → MCP Servers
        Or edit settings.json:

        {
          "cline.mcpServers": {
            "ludus": {
              "command": "/absolute/path/to/.venv/bin/ludus-fastmcp",
              "env": {
                "LUDUS_API_URL": "https://your-ludus-instance:8080",
                "LUDUS_API_KEY": "your-api-key"
              }
            }
          }
        }

STEP 5: Restart MCP Client
─────────────────────────────────────────────────────────────────────────────────
    • Close and reopen Claude Desktop or VS Code
    • The Ludus MCP tools should now be available
    • Try asking: "List my Ludus ranges"

TROUBLESHOOTING:
─────────────────────────────────────────────────────────────────────────────────
    Problem: "LUDUS_API_URL is not set"
    Solution: Ensure environment variables are set in MCP client config

    Problem: "Connection refused"
    Solution: Check LUDUS_API_URL is correct and Ludus server is running

    Problem: "Authentication failed"
    Solution: Verify LUDUS_API_KEY is correct (run: ludus user apikey)

    Problem: Tools not appearing
    Solution: Check MCP client logs for errors, restart client

For more help, visit: https://docs.ludus.cloud
""")


def _get_pid_file():
    """Get path to PID file for daemon mode."""
    return Path.home() / ".ludus-fastmcp" / "ludus-fastmcp.pid"


def _get_log_file():
    """Get path to log file for daemon mode."""
    return Path.home() / ".ludus-fastmcp" / "ludus-fastmcp.log"


def _start_daemon():
    """Start the MCP server in daemon mode."""
    pid_file = _get_pid_file()
    log_file = _get_log_file()

    # Create directory if it doesn't exist
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if already running
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            # Check if process is running
            os.kill(pid, 0)
            print(f"[ERROR] Daemon already running with PID {pid}")
            print(f"   Use 'ludus-fastmcp --stop-daemon' to stop it first")
            sys.exit(1)
        except (OSError, ValueError):
            # Process not running, remove stale PID file
            pid_file.unlink()

    # Fork process
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process
            print(f"[OK] Daemon started with PID {pid}")
            print(f"   Log file: {log_file}")
            print(f"   Use 'ludus-fastmcp --status' to check status")
            print(f"   Use 'ludus-fastmcp --stop-daemon' to stop")
            sys.exit(0)
    except OSError as e:
        print(f"[ERROR] Fork failed: {e}")
        sys.exit(1)

    # Child process continues
    # Detach from parent
    os.setsid()

    # Second fork to prevent zombie
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        print(f"[ERROR] Second fork failed: {e}")
        sys.exit(1)

    # Write PID file
    pid_file.write_text(str(os.getpid()))

    # Redirect stdout/stderr to log file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())

    # Close standard input
    sys.stdin = open("/dev/null", "r")

    print(f"\n{'=' * 60}")
    print(f"Ludus MCP Daemon Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"PID: {os.getpid()}")
    print(f"{'=' * 60}\n")


def _stop_daemon():
    """Stop the MCP server daemon."""
    pid_file = _get_pid_file()

    if not pid_file.exists():
        print("[ERROR] Daemon is not running (no PID file found)")
        sys.exit(1)

    try:
        pid = int(pid_file.read_text().strip())

        # Try to kill the process
        os.kill(pid, signal.SIGTERM)

        # Wait for process to die
        import time
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                break

        # Check if still running
        try:
            os.kill(pid, 0)
            print(f"[WARNING] Daemon (PID {pid}) did not stop gracefully, forcing...")
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

        # Remove PID file
        pid_file.unlink()
        print(f"[OK] Daemon stopped (PID {pid})")

    except (OSError, ValueError) as e:
        print(f"[ERROR] Error stopping daemon: {e}")
        pid_file.unlink()  # Remove stale PID file
        sys.exit(1)


def _check_daemon_status():
    """Check if the daemon is running."""
    pid_file = _get_pid_file()
    log_file = _get_log_file()

    if not pid_file.exists():
        print("⭕ Daemon Status: NOT RUNNING")
        return

    try:
        pid = int(pid_file.read_text().strip())

        # Check if process is running
        os.kill(pid, 0)

        print("[OK] Daemon Status: RUNNING")
        print(f"   PID:      {pid}")
        print(f"   PID File: {pid_file}")
        print(f"   Log File: {log_file}")

        # Show last few log lines
        if log_file.exists():
            print("\n📄 Recent Log Entries:")
            with open(log_file, "r") as f:
                lines = f.readlines()
                for line in lines[-10:]:
                    print(f"   {line.rstrip()}")

    except (OSError, ValueError):
        print("[WARNING] Daemon Status: STALE (PID file exists but process not running)")
        print(f"   Removing stale PID file: {pid_file}")
        pid_file.unlink()


def cli_main():
    """CLI entry point for ludus-fastmcp command.

    This is the main entry point when running:
        ludus-fastmcp
    or:
        python -m ludus_mcp.server.main
    """
    global _verbose_mode, _daemon_mode

    # Check for command-line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg in ["--help", "-h", "help"]:
            print_help()
            sys.exit(0)
        elif arg in ["--version", "-v", "version"]:
            print_version()
            sys.exit(0)
        elif arg in ["--list-tools", "-l", "list-tools"]:
            asyncio.run(list_tools_async(detailed=False))
            sys.exit(0)
        elif arg in ["--list-tools-detailed", "list-tools-detailed"]:
            asyncio.run(list_tools_async(detailed=True))
            sys.exit(0)
        elif arg in ["--setup", "setup"]:
            # Run interactive setup wizard
            from ludus_mcp.utils.setup import interactive_setup
            sys.exit(interactive_setup())
        elif arg in ["--setup-guide", "setup-guide"]:
            print_setup()
            sys.exit(0)
        elif arg in ["--verbose", "-V", "verbose"]:
            _verbose_mode = True
            # Continue to normal startup
        elif arg in ["--daemon", "-d", "daemon"]:
            _daemon_mode = True
            _verbose_mode = True  # Daemon mode implies verbose for logs
            _start_daemon()
            # _start_daemon() will exit, this line won't be reached
        elif arg in ["--stop-daemon", "stop-daemon", "stop"]:
            _stop_daemon()
            sys.exit(0)
        elif arg in ["--status", "status"]:
            _check_daemon_status()
            sys.exit(0)
        else:
            print(f"Unknown option: {arg}")
            print("Run 'ludus-fastmcp --help' for usage information")
            sys.exit(1)

    # Normal server startup
    try:
        # Initialize MCP server (this validates API credentials)
        mcp = _initialize_mcp_server()

        if _verbose_mode:
            # Count total tools
            total_tools = asyncio.run(mcp.get_tools())
            tool_count = len(total_tools)

            print("[INFO] Starting MCP Server:", file=sys.stderr)
            print(f"  - Total Tools: {tool_count}", file=sys.stderr)
            print(f"  - Transport:   STDIO", file=sys.stderr)
            print(f"  - Mode:        {'DAEMON' if _daemon_mode else 'FOREGROUND'}", file=sys.stderr)
            print(file=sys.stderr)
            print("="* 60, file=sys.stderr)
            print("[OK] MCP Server Ready - Waiting for client connection...", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print(file=sys.stderr)

        # Run the FastMCP server
        mcp.run()

    except KeyboardInterrupt:
        if _verbose_mode:
            print("\n\n⏹  Server shutting down (Ctrl+C received)...", file=sys.stderr)
        logger.info("Server shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        if _verbose_mode:
            import traceback
            traceback.print_exc()
        else:
            print(f"\n[ERROR] Server failed to start: {e}", file=sys.stderr)
            print("Run with --verbose for more details", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_main()

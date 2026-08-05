"""Unified launcher for Ludus MCP client with multiple UI modes."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    print("ERROR: click library not installed. Install with: pip install click")
    sys.exit(1)


@click.group(invoke_without_command=True, context_settings={"max_content_width": 120})
@click.option('--version', is_flag=True, help='Show version information')
@click.pass_context
def cli(ctx, version):
    """Ludus FastMCP Client - AI-Powered Cyber Range Management

\b
Features:
  - 231 FastMCP tools across 23 modules
  - Skeleton templates for VMs and ranges
  - Ansible Galaxy & custom role management
  - Enhanced AI-assisted range building

\b
Setup:
  ludus-ai setup-llm              # Setup local LLM with Ollama (interactive)

\b
Chat Interfaces:
  ludus-ai install anythingllm    # Install AnythingLLM (Recommended)
  ludus-ai install openwebui      # Install Open WebUI
  ludus-ai install opencode       # Install OpenCode AI

\b
Maintenance:
  ludus-ai clear-cache --opencode # Clear OpenCode cache
  ludus-ai clear-cache --all      # Clear all caches
  ludus-ai uninstall opencode     # Uninstall OpenCode AI
  ludus-ai uninstall anythingllm  # Uninstall AnythingLLM
  ludus-ai uninstall openwebui    # Uninstall Open WebUI

\b
Direct Tools:
  ludus-ai tool list-tools        # List all 231 FastMCP tools
  ludus-ai tool list-ranges       # List all ranges with details
  ludus-ai tool get-inventory     # Get range inventory
  ludus-ai tool call-tool <name>  # Call any FastMCP tool directly
    """
    if version:
        click.echo("Ludus FastMCP Client v1.0")
        click.echo("FastMCP Server: 231 tools")
        ctx.exit(0)

    # Store context for subcommands
    ctx.ensure_object(dict)

    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


# Web, GUI, and Chat commands removed - use AnythingLLM or Open WebUI instead


@cli.group(name='install')
def install_group():
    """
    Install professional chat interfaces for Ludus MCP.

    Choose between three community-maintained chat interfaces with beautiful
    dark themes and modern UIs.

    Examples:
        ludus-ai install anythingllm        # Install AnythingLLM (Recommended)
        ludus-ai install openwebui          # Install Open WebUI
        ludus-ai install opencode           # Install OpenCode AI
    """
    pass


@cli.group(name='uninstall')
def uninstall_group():
    """
    Uninstall chat interfaces and clean up configurations.

    Examples:
        ludus-ai uninstall opencode         # Uninstall OpenCode AI
        ludus-ai uninstall anythingllm      # Uninstall AnythingLLM
        ludus-ai uninstall openwebui        # Uninstall Open WebUI
    """
    pass


@cli.command('clear-cache')
@click.option('--all', 'clear_all', is_flag=True, help='Clear all caches (OpenCode, pipx, Python)')
@click.option('--opencode', is_flag=True, help='Clear OpenCode cache only')
@click.option('--pipx', is_flag=True, help='Clear pipx cache only')
def clear_cache(clear_all, opencode, pipx):
    """
    Clear caches for installed components.

    This clears cached data that might cause issues with updated versions.

    Examples:
        ludus-ai clear-cache --all          # Clear all caches
        ludus-ai clear-cache --opencode     # Clear OpenCode cache
        ludus-ai clear-cache --pipx         # Clear pipx cache
    """
    import shutil

    if not any([clear_all, opencode, pipx]):
        click.echo("[ERROR] Please specify which cache to clear", err=True)
        click.echo("   Use --all, --opencode, or --pipx", err=True)
        click.echo("   Run: ludus-ai clear-cache --help", err=True)
        sys.exit(1)

    cleared = []
    errors = []

    # Clear OpenCode cache
    if clear_all or opencode:
        opencode_cache = Path.home() / ".cache" / "opencode"
        if opencode_cache.exists():
            try:
                shutil.rmtree(opencode_cache)
                cleared.append(f"[OK] OpenCode cache ({opencode_cache})")
            except Exception as e:
                errors.append(f"[ERROR] OpenCode cache: {e}")
        else:
            cleared.append("[OK] OpenCode cache (already clean)")

    # Clear pipx cache
    if clear_all or pipx:
        pipx_cache = Path.home() / ".local" / "pipx" / ".cache"
        if pipx_cache.exists():
            try:
                shutil.rmtree(pipx_cache)
                cleared.append(f"[OK] Pipx cache ({pipx_cache})")
            except Exception as e:
                errors.append(f"[ERROR] Pipx cache: {e}")
        else:
            cleared.append("[OK] Pipx cache (already clean)")

    # Clear Python __pycache__
    if clear_all:
        project_root = Path.cwd()
        pycache_count = 0
        for pycache_dir in project_root.rglob("__pycache__"):
            try:
                shutil.rmtree(pycache_dir)
                pycache_count += 1
            except Exception as e:
                errors.append(f"[ERROR] {pycache_dir}: {e}")

        if pycache_count > 0:
            cleared.append(f"[OK] Removed {pycache_count} __pycache__ directories")

    # Print results
    click.echo("\n🧹 Cache Cleanup Results:\n")
    for msg in cleared:
        click.echo(f"  {msg}")

    if errors:
        click.echo("\n[WARNING] Errors:\n")
        for msg in errors:
            click.echo(f"  {msg}", err=True)

    click.echo("\n[OK] Cache cleanup complete!")

    if opencode or clear_all:
        click.echo("\n[TIP] Restart OpenCode to use the updated MCP server:")
        click.echo("   opencode")


@install_group.command('anythingllm')
def install_anythingllm():
    """
    Install AnythingLLM chat interface (Recommended).

    AnythingLLM provides a beautiful dark theme, professional UI, and native
    MCP support. Best for most users.

    Features:
    - Beautiful dark theme UI
    - Desktop app or Docker
    - Native MCP support
    - Built-in RAG capabilities
    - ChatGPT-like experience

    After installation, access at: http://localhost:3001
    """
    # Find the script relative to the package installation
    script_path = Path(__file__).parent.parent / "scripts" / "install-anythingllm.sh"

    # If not found, try relative to current working directory
    if not script_path.exists():
        script_path = Path.cwd() / "scripts" / "install-anythingllm.sh"

    if not script_path.exists():
        click.echo("[ERROR] Installation script not found.", err=True)
        click.echo(f"   Expected location: {script_path}", err=True)
        click.echo("\nPlease ensure you're running this from the ludus-fastmcp directory,", err=True)
        click.echo("or run the script manually:", err=True)
        click.echo("   ./scripts/install-anythingllm.sh", err=True)
        sys.exit(1)

    click.echo("[INFO] Installing AnythingLLM...")
    click.echo(f"[INFO] Script: {script_path}\n")

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            check=False,
            env=os.environ.copy()
        )

        if result.returncode == 0:
            click.echo("\n[OK] AnythingLLM installation complete!")
            click.echo("   Access at: http://localhost:3001")
            
            # Configure MCP server
            click.echo("\n[INFO] Configuring Ludus FastMCP server...")
            try:
                from ludus_mcp.utils.mcp_config import configure_anythingllm
                success, message = configure_anythingllm(overwrite=False)
                if success:
                    click.echo(f"[OK] {message}")
                else:
                    click.echo(f"[WARNING] {message}", err=True)
                    click.echo("   You can configure it manually later.", err=True)
            except Exception as e:
                click.echo(f"[WARNING] Failed to auto-configure MCP: {e}", err=True)
                click.echo("   You can configure it manually later.", err=True)
        else:
            click.echo(f"\n[ERROR] Installation failed with exit code {result.returncode}", err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(f"\n[ERROR] Error during installation: {e}", err=True)
        sys.exit(1)


@install_group.command('openwebui')
def install_openwebui():
    """
    Install Open WebUI chat interface.

    Open WebUI provides a gorgeous modern UI with extensive customization
    options. Best for teams and production environments.

    Features:
    - Gorgeous modern dark theme
    - Multi-user support
    - Extensive customization
    - Production-ready
    - Web-only interface

    After installation, access at: http://localhost:3000
    """
    # Find the script relative to the package installation
    script_path = Path(__file__).parent.parent / "scripts" / "install-openwebui.sh"

    # If not found, try relative to current working directory
    if not script_path.exists():
        script_path = Path.cwd() / "scripts" / "install-openwebui.sh"

    if not script_path.exists():
        click.echo("[ERROR] Installation script not found.", err=True)
        click.echo(f"   Expected location: {script_path}", err=True)
        click.echo("\nPlease ensure you're running this from the ludus-fastmcp directory,", err=True)
        click.echo("or run the script manually:", err=True)
        click.echo("   ./scripts/install-openwebui.sh", err=True)
        sys.exit(1)

    click.echo("[INFO] Installing Open WebUI...")
    click.echo(f"[INFO] Script: {script_path}\n")

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            check=False,
            env=os.environ.copy()
        )

        if result.returncode == 0:
            click.echo("\n[OK] Open WebUI installation complete!")
            click.echo("   Access at: http://localhost:3000")
            
            # Configure MCP server
            click.echo("\n[INFO] Configuring Ludus FastMCP server...")
            try:
                from ludus_mcp.utils.mcp_config import configure_openwebui
                success, message = configure_openwebui(overwrite=False)
                if success:
                    click.echo(f"[OK] {message}")
                else:
                    click.echo(f"[WARNING] {message}", err=True)
                    click.echo("   You can configure it manually later.", err=True)
            except Exception as e:
                click.echo(f"[WARNING] Failed to auto-configure MCP: {e}", err=True)
                click.echo("   You can configure it manually later.", err=True)
        else:
            click.echo(f"\n[ERROR] Installation failed with exit code {result.returncode}", err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(f"\n[ERROR] Error during installation: {e}", err=True)
        sys.exit(1)


@install_group.command('opencode')
def install_opencode():
    """
    Install OpenCode AI terminal agent.

    OpenCode AI is a powerful terminal-native AI coding agent with native
    MCP support. Best for developers who prefer terminal-based workflows.

    Features:
    - Terminal-native AI agent
    - Native MCP support
    - LSP integration
    - Multi-session support
    - 75+ LLM providers
    - Privacy-first, local execution

    After installation, run: opencode
    """
    # Find the script relative to the package installation
    script_path = Path(__file__).parent.parent / "scripts" / "install-opencode.sh"

    # If not found, try relative to current working directory
    if not script_path.exists():
        script_path = Path.cwd() / "scripts" / "install-opencode.sh"

    if not script_path.exists():
        click.echo("[ERROR] Installation script not found.", err=True)
        click.echo(f"   Expected location: {script_path}", err=True)
        click.echo("\nPlease ensure you're running this from the ludus-fastmcp directory,", err=True)
        click.echo("or run the script manually:", err=True)
        click.echo("   ./scripts/install-opencode.sh", err=True)
        sys.exit(1)

    click.echo("[INFO] Installing OpenCode AI...")
    click.echo(f"[INFO] Script: {script_path}\n")

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            check=False,
            env=os.environ.copy()
        )

        if result.returncode == 0:
            click.echo("\n[OK] OpenCode AI installation complete!")
            click.echo("   Run: opencode")
            
            # Configure MCP server
            click.echo("\n[INFO] Configuring Ludus FastMCP server...")
            try:
                from ludus_mcp.utils.mcp_config import configure_opencode
                success, message = configure_opencode(overwrite=False)
                if success:
                    click.echo(f"[OK] {message}")
                else:
                    click.echo(f"[WARNING] {message}", err=True)
                    click.echo("   You can configure it manually later.", err=True)
            except Exception as e:
                click.echo(f"[WARNING] Failed to auto-configure MCP: {e}", err=True)
                click.echo("   You can configure it manually later.", err=True)
        else:
            click.echo(f"\n[ERROR] Installation failed with exit code {result.returncode}", err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(f"\n[ERROR] Error during installation: {e}", err=True)
        sys.exit(1)


@uninstall_group.command('opencode')
@click.option('--keep-config', is_flag=True, help='Keep OpenCode configuration files')
def uninstall_opencode(keep_config):
    """
    Uninstall OpenCode AI and optionally remove configuration.

    This will:
    - Uninstall OpenCode AI binary
    - Optionally remove configuration files (unless --keep-config is used)
    - Clear OpenCode cache

    Examples:
        ludus-ai uninstall opencode              # Full uninstall
        ludus-ai uninstall opencode --keep-config  # Keep configs
    """
    import shutil

    click.echo("🗑️  Uninstalling OpenCode AI...\n")

    removed = []
    errors = []

    # Uninstall OpenCode binary
    opencode_bin = Path.home() / ".opencode"
    if opencode_bin.exists():
        try:
            shutil.rmtree(opencode_bin)
            removed.append(f"[OK] OpenCode binary ({opencode_bin})")
        except Exception as e:
            errors.append(f"[ERROR] OpenCode binary: {e}")
    else:
        removed.append("[OK] OpenCode binary (not found)")

    # Remove configuration (unless --keep-config)
    if not keep_config:
        opencode_config = Path.home() / ".config" / "opencode"
        if opencode_config.exists():
            try:
                shutil.rmtree(opencode_config)
                removed.append(f"[OK] OpenCode config ({opencode_config})")
            except Exception as e:
                errors.append(f"[ERROR] OpenCode config: {e}")
        else:
            removed.append("[OK] OpenCode config (not found)")
    else:
        click.echo("ℹ️  Keeping OpenCode configuration files")

    # Clear cache
    opencode_cache = Path.home() / ".cache" / "opencode"
    if opencode_cache.exists():
        try:
            shutil.rmtree(opencode_cache)
            removed.append(f"[OK] OpenCode cache ({opencode_cache})")
        except Exception as e:
            errors.append(f"[ERROR] OpenCode cache: {e}")

    # Print results
    click.echo("\n[INFO] Uninstall Results:\n")
    for msg in removed:
        click.echo(f"  {msg}")

    if errors:
        click.echo("\n[WARNING] Errors:\n")
        for msg in errors:
            click.echo(f"  {msg}", err=True)

    if errors:
        click.echo("\n[WARNING] Uninstall completed with errors")
        sys.exit(1)
    else:
        click.echo("\n[OK] OpenCode AI uninstalled successfully!")


@uninstall_group.command('anythingllm')
@click.option('--keep-data', is_flag=True, help='Keep AnythingLLM data and configurations')
def uninstall_anythingllm(keep_data):
    """
    Uninstall AnythingLLM and optionally remove data.

    This will:
    - Stop and remove AnythingLLM Docker container
    - Optionally remove data directory (unless --keep-data is used)

    Examples:
        ludus-ai uninstall anythingllm              # Full uninstall
        ludus-ai uninstall anythingllm --keep-data  # Keep data
    """
    click.echo("🗑️  Uninstalling AnythingLLM...\n")

    removed = []
    errors = []

    # Stop and remove Docker container
    try:
        result = subprocess.run(
            ["docker", "stop", "anythingllm"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            removed.append("[OK] Stopped AnythingLLM container")
    except Exception as e:
        errors.append(f"[ERROR] Stop container: {e}")

    try:
        result = subprocess.run(
            ["docker", "rm", "anythingllm"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            removed.append("[OK] Removed AnythingLLM container")
    except Exception as e:
        errors.append(f"[ERROR] Remove container: {e}")

    # Remove data (unless --keep-data)
    if not keep_data:
        import shutil
        anythingllm_data = Path.home() / ".anythingllm"
        if anythingllm_data.exists():
            try:
                shutil.rmtree(anythingllm_data)
                removed.append(f"[OK] AnythingLLM data ({anythingllm_data})")
            except Exception as e:
                errors.append(f"[ERROR] AnythingLLM data: {e}")
    else:
        click.echo("ℹ️  Keeping AnythingLLM data directory")

    # Print results
    click.echo("\n[INFO] Uninstall Results:\n")
    for msg in removed:
        click.echo(f"  {msg}")

    if errors:
        click.echo("\n[WARNING] Errors:\n")
        for msg in errors:
            click.echo(f"  {msg}", err=True)

    if errors:
        click.echo("\n[WARNING] Uninstall completed with errors")
        sys.exit(1)
    else:
        click.echo("\n[OK] AnythingLLM uninstalled successfully!")


@uninstall_group.command('openwebui')
@click.option('--keep-data', is_flag=True, help='Keep Open WebUI data and configurations')
def uninstall_openwebui(keep_data):
    """
    Uninstall Open WebUI and optionally remove data.

    This will:
    - Stop and remove Open WebUI Docker container
    - Optionally remove data directory (unless --keep-data is used)

    Examples:
        ludus-ai uninstall openwebui              # Full uninstall
        ludus-ai uninstall openwebui --keep-data  # Keep data
    """
    click.echo("🗑️  Uninstalling Open WebUI...\n")

    removed = []
    errors = []

    # Stop and remove Docker container
    try:
        result = subprocess.run(
            ["docker", "stop", "open-webui"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            removed.append("[OK] Stopped Open WebUI container")
    except Exception as e:
        errors.append(f"[ERROR] Stop container: {e}")

    try:
        result = subprocess.run(
            ["docker", "rm", "open-webui"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            removed.append("[OK] Removed Open WebUI container")
    except Exception as e:
        errors.append(f"[ERROR] Remove container: {e}")

    # Remove data (unless --keep-data)
    if not keep_data:
        import shutil
        openwebui_data = Path.home() / ".open-webui"
        if openwebui_data.exists():
            try:
                shutil.rmtree(openwebui_data)
                removed.append(f"[OK] Open WebUI data ({openwebui_data})")
            except Exception as e:
                errors.append(f"[ERROR] Open WebUI data: {e}")
    else:
        click.echo("ℹ️  Keeping Open WebUI data directory")

    # Print results
    click.echo("\n[INFO] Uninstall Results:\n")
    for msg in removed:
        click.echo(f"  {msg}")

    if errors:
        click.echo("\n[WARNING] Errors:\n")
        for msg in errors:
            click.echo(f"  {msg}", err=True)

    if errors:
        click.echo("\n[WARNING] Uninstall completed with errors")
        sys.exit(1)
    else:
        click.echo("\n[OK] Open WebUI uninstalled successfully!")


@cli.command('setup-llm')
def setup_llm():
    """
    Setup local LLM with Ollama (interactive).

    This interactive script will:
    - Check if Ollama is installed and running
    - Show available models
    - Help you download a recommended model
    - Verify your configuration
    - Provide next steps for each chat interface

    Recommended models:
    - qwen2.5-coder:7b (Best for coding/Ludus tasks)
    - llama3.2:3b (Fast, low RAM)
    - deepseek-coder-v2:16b (Most capable, high RAM)

    After setup, all three interfaces (OpenCode, AnythingLLM, Open WebUI)
    can use your local LLM via Ollama.
    """
    # Find the script relative to the package installation
    script_path = Path(__file__).parent.parent / "scripts" / "setup-local-llm.sh"

    # If not found, try relative to current working directory
    if not script_path.exists():
        script_path = Path.cwd() / "scripts" / "setup-local-llm.sh"

    if not script_path.exists():
        click.echo("[ERROR] setup-local-llm.sh script not found", err=True)
        click.echo("   Expected locations:", err=True)
        click.echo(f"   - {Path(__file__).parent.parent / 'scripts' / 'setup-local-llm.sh'}", err=True)
        click.echo("   - ./scripts/setup-local-llm.sh", err=True)
        sys.exit(1)

    click.echo("[INFO] Setting up local LLM with Ollama...")
    click.echo(f"[INFO] Script: {script_path}\n")

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            check=False,
            env=os.environ.copy()
        )

        if result.returncode != 0:
            click.echo(f"\n[ERROR] Setup failed with exit code {result.returncode}", err=True)
            sys.exit(result.returncode)

    except Exception as e:
        click.echo(f"\n[ERROR] Error during setup: {e}", err=True)
        sys.exit(1)


@cli.group(name='tool')
def tool_group():
    """
    Execute Ludus MCP tools directly (for scripting).

    This provides direct tool execution without interactive chat.
    Perfect for scripts and automation.

    Examples:
        ludus-ai tool list-tools
        ludus-ai tool list-scenarios
        ludus-ai tool list-ranges
    """
    pass


@tool_group.command('list-tools')
@click.option('--command', default='ludus-fastmcp', help='FastMCP server command (default: ludus-fastmcp)')
@click.option('--env', multiple=True, help='Environment variables (KEY=VALUE)')
def list_tools(command, env):
    """List all available FastMCP tools (125 total)."""
    async def _run():
        from ludus_mcp.mcp_client.unified_client import UnifiedMCPClient

        env_dict = {}
        for e in env:
            if '=' in e:
                key, value = e.split('=', 1)
                env_dict[key] = value

        async with UnifiedMCPClient(command=command, env=env_dict) as client:
            tools = await client.list_tools()
            click.echo("\nAvailable Ludus MCP Tools:\n")
            for tool in tools:
                click.echo(f"  - {tool['name']}")
                if 'description' in tool:
                    click.echo(f"    {tool['description']}")
                click.echo()

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"[ERROR] Error: {e}", err=True)
        sys.exit(1)


@tool_group.command('list-scenarios')
@click.option('--command', default='ludus-fastmcp', help='FastMCP server command (default: ludus-fastmcp)')
@click.option('--env', multiple=True, help='Environment variables (KEY=VALUE)')
def list_scenarios(command, env):
    """List all available scenarios."""
    async def _run():
        from ludus_mcp.mcp_client.unified_client import UnifiedMCPClient
        import json

        env_dict = {}
        for e in env:
            if '=' in e:
                key, value = e.split('=', 1)
                env_dict[key] = value

        async with UnifiedMCPClient(command=command, env=env_dict) as client:
            result = await client.call_tool("ludus.list_scenarios", {})
            click.echo("\nAvailable Scenarios:\n")

            # Parse the result dict from UnifiedMCPClient
            if isinstance(result, dict) and 'result' in result:
                # Parse the JSON string result
                try:
                    result_data = json.loads(result['result'])
                    if 'error' in result_data:
                        click.echo(f"[ERROR] Error: {result_data['error']}", err=True)
                    else:
                        click.echo(json.dumps(result_data, indent=2))
                except json.JSONDecodeError:
                    click.echo(result['result'])
            else:
                click.echo(json.dumps(result, indent=2))

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"[ERROR] Error: {e}", err=True)
        sys.exit(1)


@tool_group.command('get-inventory')
@click.option('--command', default='ludus-fastmcp', help='FastMCP server command (default: ludus-fastmcp)')
@click.option('--env', multiple=True, help='Environment variables (KEY=VALUE)')
def get_inventory(command, env):
    """Get Ansible inventory for your range."""
    async def _run():
        from ludus_mcp.mcp_client.unified_client import UnifiedMCPClient
        import json

        env_dict = {}
        for e in env:
            if '=' in e:
                key, value = e.split('=', 1)
                env_dict[key] = value

        async with UnifiedMCPClient(command=command, env=env_dict) as client:
            result = await client.call_tool("ludus.get_range_ansible_inventory", {})
            click.echo("\nAnsible Inventory:\n")

            # Parse the result dict from UnifiedMCPClient
            if isinstance(result, dict) and 'result' in result:
                # Parse the JSON string result
                try:
                    result_data = json.loads(result['result'])
                    if 'error' in result_data:
                        click.echo(f"[ERROR] Error: {result_data['error']}", err=True)
                    else:
                        click.echo(json.dumps(result_data, indent=2))
                except json.JSONDecodeError:
                    click.echo(result['result'])
            else:
                click.echo(json.dumps(result, indent=2))

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"[ERROR] Error: {e}", err=True)
        sys.exit(1)


@tool_group.command('list-ranges')
@click.option('--command', default='ludus-fastmcp', help='FastMCP server command (default: ludus-fastmcp)')
@click.option('--env', multiple=True, help='Environment variables (KEY=VALUE)')
def list_ranges(command, env):
    """List all ranges (uses new range management tools)."""
    async def _run():
        from ludus_mcp.mcp_client.unified_client import UnifiedMCPClient
        import json

        env_dict = {}
        for e in env:
            if '=' in e:
                key, value = e.split('=', 1)
                env_dict[key] = value

        async with UnifiedMCPClient(command=command, env=env_dict) as client:
            result = await client.call_tool("ludus.list_ranges", {})
            click.echo("\nAvailable Ranges:\n")

            # Parse the result dict from UnifiedMCPClient
            if isinstance(result, dict) and 'result' in result:
                # Parse the JSON string result
                try:
                    result_data = json.loads(result['result'])
                    if 'error' in result_data:
                        click.echo(f"[ERROR] Error: {result_data['error']}", err=True)
                    else:
                        click.echo(json.dumps(result_data, indent=2))
                except json.JSONDecodeError:
                    click.echo(result['result'])
            else:
                click.echo(json.dumps(result, indent=2))

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"[ERROR] Error: {e}", err=True)
        sys.exit(1)


@tool_group.command('call-tool')
@click.argument('tool_name')
@click.option('--args', default='{}', help='Tool arguments as JSON')
@click.option('--command', default='ludus-fastmcp', help='FastMCP server command (default: ludus-fastmcp)')
@click.option('--env', multiple=True, help='Environment variables (KEY=VALUE)')
def call_tool(tool_name, args, command, env):
    """Call a specific FastMCP tool with arguments (125 tools available).

    Example:
        ludus-ai tool call-tool list_all_ranges_detailed
        ludus-ai tool call-tool create_custom_os_template --args '{"name": "kali-custom", "os_type": "debian"}'
    """
    async def _run():
        from ludus_mcp.mcp_client.unified_client import UnifiedMCPClient
        import json

        env_dict = {}
        for e in env:
            if '=' in e:
                key, value = e.split('=', 1)
                env_dict[key] = value

        # Parse the JSON arguments
        try:
            tool_args = json.loads(args)
        except json.JSONDecodeError as e:
            click.echo(f"[ERROR] Invalid JSON arguments: {e}", err=True)
            sys.exit(1)

        async with UnifiedMCPClient(command=command, env=env_dict) as client:
            click.echo(f"\nCalling tool: {tool_name}")
            if tool_args:
                click.echo(f"Arguments: {json.dumps(tool_args, indent=2)}\n")

            result = await client.call_tool(tool_name, tool_args)

            # Parse the result dict from UnifiedMCPClient
            if isinstance(result, dict) and 'result' in result:
                # Parse the JSON string result
                try:
                    result_data = json.loads(result['result'])
                    if 'error' in result_data:
                        click.echo(f"\n[ERROR] Error: {result_data['error']}", err=True)
                    else:
                        click.echo(f"\nResult:\n{json.dumps(result_data, indent=2)}")
                except json.JSONDecodeError:
                    click.echo(f"\nResult:\n{result['result']}")
            else:
                click.echo(f"\nResult:\n{json.dumps(result, indent=2)}")

    try:
        asyncio.run(_run())
    except Exception as e:
        click.echo(f"[ERROR] Error: {e}", err=True)
        sys.exit(1)


# Sessions command removed - session management is handled by AnythingLLM or Open WebUI


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

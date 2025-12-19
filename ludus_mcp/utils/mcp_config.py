"""Utility for automatically configuring MCP clients (VS Code, Claude Desktop)."""

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

from ludus_mcp.utils.config import get_settings
from ludus_mcp.utils.logging import get_logger

logger = get_logger(__name__)


def get_claude_desktop_config_path() -> Path | None:
    """Get the Claude Desktop configuration file path based on OS."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Claude/claude_desktop_config.json"
        return None
    elif system == "Linux":
        return Path.home() / ".config/Claude/claude_desktop_config.json"
    else:
        logger.warning(f"Unknown OS: {system}")
        return None


def get_vscode_config_paths() -> dict[str, Path]:
    """Get VS Code MCP configuration file paths for different extensions."""
    system = platform.system()
    base_config = Path.home() / ".config"
    
    if system == "Windows":
        base_config = Path(os.getenv("APPDATA", "")) / "Code/User"
    elif system == "Darwin":  # macOS
        base_config = Path.home() / "Library/Application Support/Code/User"
    elif system == "Linux":
        base_config = Path.home() / ".config/Code/User"
    
    return {
        "github_copilot": base_config / "globalStorage/github.copilot/settings/mcp.json",
        "claude_dev": base_config / "globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json",
        "official": base_config / "settings.json",
    }


def load_json_config(config_path: Path) -> dict[str, Any]:
    """Load JSON configuration file, creating empty dict if it doesn't exist."""
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_path}: {e}")
            return {}
    return {}


def save_json_config(config_path: Path, config: dict[str, Any]) -> bool:
    """Save JSON configuration file, creating parent directories if needed."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")
        return False


def get_ludus_fastmcp_command() -> str:
    """Get the full path to ludus-fastmcp command."""
    # Try to find the command
    cmd = shutil.which("ludus-fastmcp")
    if cmd:
        return cmd
    
    # Try common locations
    common_paths = [
        Path.home() / ".local" / "bin" / "ludus-fastmcp",
        Path("/usr/local/bin/ludus-fastmcp"),
        Path("/usr/bin/ludus-fastmcp"),
    ]
    
    for path in common_paths:
        if path.exists():
            return str(path)
    
    # Default to just the command name (assumes it's in PATH)
    return "ludus-fastmcp"


def generate_ludus_mcp_config(include_llm: bool = False) -> dict[str, Any]:
    """Generate Ludus MCP server configuration."""
    settings = get_settings()
    
    config = {
        "command": get_ludus_fastmcp_command(),
        "env": {
            "LUDUS_API_URL": settings.ludus_api_url,
            "LUDUS_API_KEY": settings.ludus_api_key,
            "LOG_LEVEL": settings.log_level,
        }
    }
    
    # Add LLM configuration if requested and available
    if include_llm and hasattr(settings, "llm_provider_type") and settings.llm_provider_type:
        if settings.llm_provider_type in ["openai", "anthropic", "google"]:
            if hasattr(settings, "llm_api_key") and settings.llm_api_key:
                config["env"]["LLM_PROVIDER_TYPE"] = settings.llm_provider_type
                config["env"]["LLM_API_KEY"] = settings.llm_api_key
                if hasattr(settings, "llm_model") and settings.llm_model:
                    config["env"]["LLM_MODEL"] = settings.llm_model
        elif settings.llm_provider_type in ["llama-cpp", "gpt4all"]:
            if hasattr(settings, "llm_model_path") and settings.llm_model_path:
                config["env"]["LLM_PROVIDER_TYPE"] = settings.llm_provider_type
                config["env"]["LLM_MODEL_PATH"] = settings.llm_model_path
                if hasattr(settings, "llm_context_size") and settings.llm_context_size:
                    config["env"]["LLM_CONTEXT_SIZE"] = str(settings.llm_context_size)
        elif settings.llm_provider_type == "ollama":
            config["env"]["LLM_PROVIDER_TYPE"] = "ollama"
            if hasattr(settings, "llm_ollama_base_url") and settings.llm_ollama_base_url:
                config["env"]["LLM_OLLAMA_BASE_URL"] = settings.llm_ollama_base_url
            if hasattr(settings, "llm_model") and settings.llm_model:
                config["env"]["LLM_MODEL"] = settings.llm_model
    
    return config


def configure_claude_desktop(include_llm: bool = False, overwrite: bool = False) -> tuple[bool, str]:
    """Configure Claude Desktop MCP settings."""
    config_path = get_claude_desktop_config_path()
    
    if not config_path:
        return False, "Could not determine Claude Desktop config path for this OS"
    
    # Load existing config
    existing_config = load_json_config(config_path)
    
    # Check if ludus-fastmcp already exists
    if "mcpServers" in existing_config and "ludus-fastmcp" in existing_config["mcpServers"]:
        if not overwrite:
            return False, f"ludus-fastmcp already configured in {config_path}. Use --overwrite to replace."
    
    # Generate new config
    ludus_config = generate_ludus_mcp_config(include_llm)
    
    # Merge with existing
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["ludus-fastmcp"] = ludus_config
    
    # Save
    if save_json_config(config_path, existing_config):
        return True, f"Configuration saved to {config_path}"
    else:
        return False, f"Failed to save configuration to {config_path}"


def configure_vscode(
    extension: str = "github_copilot",
    include_llm: bool = False,
    overwrite: bool = False,
) -> tuple[bool, str]:
    """Configure VS Code MCP settings for a specific extension."""
    paths = get_vscode_config_paths()
    
    if extension not in paths:
        return False, f"Unknown extension: {extension}. Available: {', '.join(paths.keys())}"
    
    config_path = paths[extension]
    
    # Load existing config
    existing_config = load_json_config(config_path)
    
    # Check if ludus-fastmcp already exists
    if "mcpServers" in existing_config and "ludus-fastmcp" in existing_config["mcpServers"]:
        if not overwrite:
            return False, f"ludus-fastmcp already configured in {config_path}. Use --overwrite to replace."
    
    # Generate new config
    ludus_config = generate_ludus_mcp_config(include_llm)
    
    # Merge with existing
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["ludus-fastmcp"] = ludus_config
    
    # Save
    if save_json_config(config_path, existing_config):
        # Also update VS Code settings.json to enable GitHub Copilot discovery
        if extension == "github_copilot":
            _enable_vscode_mcp_discovery()
        return True, f"Configuration saved to {config_path}"
    else:
        return False, f"Failed to save configuration to {config_path}"


def _enable_vscode_mcp_discovery() -> None:
    """Enable GitHub Copilot MCP discovery in VS Code settings.json."""
    system = platform.system()
    if system == "Windows":
        settings_path = Path(os.getenv("APPDATA", "")) / "Code/User/settings.json"
    elif system == "Darwin":  # macOS
        settings_path = Path.home() / "Library/Application Support/Code/User/settings.json"
    else:  # Linux
        settings_path = Path.home() / ".config/Code/User/settings.json"
    
    if not settings_path.exists():
        return
    
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except (json.JSONDecodeError, IOError):
        return
    
    # Enable GitHub Copilot discovery
    if "chat.mcp.discovery.enabled" not in settings:
        settings["chat.mcp.discovery.enabled"] = {}
    
    settings["chat.mcp.discovery.enabled"]["github.copilot"] = True
    
    # Enable autostart
    if "chat.mcp.autostart.experimental" not in settings:
        settings["chat.mcp.autostart.experimental"] = True
    
    try:
        with open(settings_path, 'w') as f:
            json.dump(settings, f, indent=4)
        logger.info(f"Enabled GitHub Copilot MCP discovery in {settings_path}")
    except IOError:
        logger.warning(f"Could not update VS Code settings.json")


def configure_all_mcp_clients(include_llm: bool = False, overwrite: bool = False) -> dict[str, tuple[bool, str]]:
    """Configure all available MCP clients."""
    results = {}
    
    # Claude Desktop
    claude_path = get_claude_desktop_config_path()
    if claude_path and claude_path.parent.exists():
        success, message = configure_claude_desktop(include_llm, overwrite)
        results["claude_desktop"] = (success, message)
    else:
        results["claude_desktop"] = (False, "Claude Desktop config directory not found")
    
    # VS Code extensions
    paths = get_vscode_config_paths()
    for ext_name, ext_path in paths.items():
        if ext_path.parent.exists():
            success, message = configure_vscode(ext_name, include_llm, overwrite)
            results[f"vscode_{ext_name}"] = (success, message)
        else:
            results[f"vscode_{ext_name}"] = (False, f"VS Code {ext_name} config directory not found")
    
    return results


def list_available_clients() -> dict[str, Path | None]:
    """List all available MCP client configuration paths."""
    clients = {}
    
    # Claude Desktop
    claude_path = get_claude_desktop_config_path()
    clients["claude_desktop"] = claude_path if (claude_path and claude_path.parent.exists()) else None
    
    # VS Code
    paths = get_vscode_config_paths()
    for ext_name, ext_path in paths.items():
        key = f"vscode_{ext_name}"
        clients[key] = ext_path if ext_path.parent.exists() else None
    
    return clients


def configure_openwebui(overwrite: bool = False) -> tuple[bool, str]:
    """Configure OpenWebUI MCP server settings.
    
    OpenWebUI uses native MCP support. This creates a configuration file
    that can be imported into OpenWebUI's MCP server settings.
    
    Returns:
        Tuple of (success, message)
    """
    config_dir = Path.home() / ".config" / "ludus-fastmcp"
    config_file = config_dir / "openwebui-mcp-config.json"
    
    # Generate configuration
    ludus_config = generate_ludus_mcp_config(include_llm=False)
    
    # OpenWebUI expects a specific format
    config = {
        "name": "ludus-fastmcp",
        "command": ludus_config["command"],
        "env": ludus_config["env"]
    }
    
    # Check if already exists
    if config_file.exists() and not overwrite:
        return False, f"Configuration already exists at {config_file}. Use --overwrite to replace."
    
    # Save configuration
    if save_json_config(config_file, config):
        return True, f"OpenWebUI MCP configuration saved to {config_file}\n" \
                    f"To use in OpenWebUI:\n" \
                    f"1. Open http://localhost:3000\n" \
                    f"2. Go to Settings → Tools → MCP Servers\n" \
                    f"3. Click '+ Add MCP Server'\n" \
                    f"4. Use:\n" \
                    f"   Name: ludus-fastmcp\n" \
                    f"   Command: {config['command']}\n" \
                    f"   Environment Variables:\n" \
                    f"     LUDUS_API_URL={config['env']['LUDUS_API_URL']}\n" \
                    f"     LUDUS_API_KEY={config['env']['LUDUS_API_KEY']}\n" \
                    f"     LOG_LEVEL={config['env']['LOG_LEVEL']}"
    else:
        return False, f"Failed to save configuration to {config_file}"


def configure_opencode(overwrite: bool = False) -> tuple[bool, str]:
    """Configure OpenCode AI MCP server settings.
    
    OpenCode uses a JSON configuration file for MCP servers.
    
    Returns:
        Tuple of (success, message)
    """
    opencode_config_dir = Path.home() / ".config" / "opencode"
    config_file = opencode_config_dir / "mcp_servers.json"
    
    # Generate configuration
    ludus_config = generate_ludus_mcp_config(include_llm=False)
    
    # Load existing config if it exists
    existing_config = load_json_config(config_file)
    
    # Check if already exists
    if "mcpServers" in existing_config and "ludus-fastmcp" in existing_config.get("mcpServers", {}):
        if not overwrite:
            return False, f"ludus-fastmcp already configured in {config_file}. Use --overwrite to replace."
    
    # Merge with existing
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["ludus-fastmcp"] = {
        "command": ludus_config["command"],
        "env": ludus_config["env"]
    }
    
    # Save configuration
    if save_json_config(config_file, existing_config):
        return True, f"OpenCode MCP configuration saved to {config_file}\n" \
                    f"Restart OpenCode to use the MCP server."
    else:
        return False, f"Failed to save configuration to {config_file}"


def configure_anythingllm(overwrite: bool = False) -> tuple[bool, str]:
    """Configure AnythingLLM MCP server settings.
    
    AnythingLLM uses a JSON configuration file for MCP servers.
    The configuration is stored in the AnythingLLM data directory.
    
    Returns:
        Tuple of (success, message)
    """
    anythingllm_dir = Path.home() / ".anythingllm"
    config_file = anythingllm_dir / "mcp_servers.json"
    
    # Generate configuration
    ludus_config = generate_ludus_mcp_config(include_llm=False)
    
    # Load existing config if it exists
    existing_config = load_json_config(config_file)
    
    # Check if already exists
    if "mcpServers" in existing_config and "ludus-fastmcp" in existing_config.get("mcpServers", {}):
        if not overwrite:
            return False, f"ludus-fastmcp already configured in {config_file}. Use --overwrite to replace."
    
    # Merge with existing
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    existing_config["mcpServers"]["ludus-fastmcp"] = {
        "command": ludus_config["command"],
        "env": ludus_config["env"]
    }
    
    # Save configuration
    if save_json_config(config_file, existing_config):
        return True, f"AnythingLLM MCP configuration saved to {config_file}\n" \
                    f"Restart AnythingLLM to use the MCP server."
    else:
        return False, f"Failed to save configuration to {config_file}"


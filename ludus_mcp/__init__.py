"""Ludus MCP - AI-Powered Cyber Range Automation.

This package provides a Model Context Protocol (MCP) server for Ludus,
enabling AI assistants to manage cyber ranges through natural language.

Package Structure:
- server: MCP server implementation
- core: Core Ludus API client (no MCP dependencies)
- mcp_client: MCP client implementations
- ui: User interface layers (web, GUI, chat)
"""

__version__ = "0.2.0"

from .core.client import LudusAPIClient
from .mcp_client.connection_manager import MCPConnectionManager
from .mcp_client.health_monitor import HealthMonitor

__all__ = [
    "LudusAPIClient",
    "MCPConnectionManager",
    "HealthMonitor",
]

"""
MCP (Model Context Protocol) Management Module

This module provides functionality for managing stdio-based MCP servers:
- GitHub repository cloning and dependency installation
- Process lifecycle management
- HTTP adapter for stdio MCP servers
- Integration with Kong Gateway
"""

from .git_manager import GitManager
from .process_manager import ProcessManager
from .stdio_client import MCPStdioClient
from .http_adapter import HTTPAdapter

__all__ = [
    "GitManager",
    "ProcessManager",
    "MCPStdioClient",
    "HTTPAdapter",
]



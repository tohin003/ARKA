"""ARKA Tools Module - Bash, File, Browser, MCP"""

from arka.tools.base_tool import (
    BaseTool,
    ToolResult,
    ToolCategory,
    ToolRegistry,
    get_tool_registry,
)
from arka.tools.bash_tool import BashTool
from arka.tools.file_tool import FileTool
from arka.tools.browser_tool import BrowserTool
from arka.tools.mcp_client import MCPClient

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolCategory",
    "ToolRegistry",
    "get_tool_registry",
    "BashTool",
    "FileTool",
    "BrowserTool",
    "MCPClient",
]


def register_default_tools():
    """Register all default tools to the global registry."""
    registry = get_tool_registry()
    registry.register(BashTool())
    registry.register(FileTool())
    registry.register(BrowserTool())
    registry.register(MCPClient())
    return registry

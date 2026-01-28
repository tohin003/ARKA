"""
ARKA MCP Client
Connect to and interact with MCP (Model Context Protocol) servers.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from arka.tools.base_tool import BaseTool, ToolResult, ToolCategory


@dataclass
class MCPServer:
    """MCP server connection info."""
    name: str
    url: str
    tools: List[Dict[str, Any]] = field(default_factory=list)
    connected: bool = False


@dataclass
class MCPToolCall:
    """Result of an MCP tool call."""
    server: str
    tool: str
    result: Any
    success: bool
    error: Optional[str] = None


class MCPClient(BaseTool):
    """
    Model Context Protocol client.
    Connects to MCP servers and exposes their tools.
    """
    
    NAME = "mcp"
    DESCRIPTION = "Connect to MCP servers and use their tools"
    CATEGORY = ToolCategory.MCP
    REQUIRES_CONFIRMATION = False
    
    def __init__(self):
        super().__init__()
        self._servers: Dict[str, MCPServer] = {}
        self._ws_connections: Dict[str, Any] = {}
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["connect", "disconnect", "list", "call"],
                    "description": "MCP action to perform",
                },
                "server_url": {
                    "type": "string",
                    "description": "URL of the MCP server",
                },
                "server_name": {
                    "type": "string",
                    "description": "Name/alias for the server",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool to call",
                },
                "tool_args": {
                    "type": "object",
                    "description": "Arguments for the tool call",
                },
            },
            "required": ["action"],
        }
    
    def execute(
        self,
        action: str,
        server_url: Optional[str] = None,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Execute an MCP action.
        
        Args:
            action: connect, disconnect, list, call
            server_url: URL for connection
            server_name: Server name/alias
            tool_name: Tool to call
            tool_args: Arguments for tool
            
        Returns:
            ToolResult with action result
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._execute_async(action, server_url, server_name, tool_name, tool_args)
        )
    
    async def _execute_async(
        self,
        action: str,
        server_url: Optional[str],
        server_name: Optional[str],
        tool_name: Optional[str],
        tool_args: Optional[Dict[str, Any]],
    ) -> ToolResult:
        """Async MCP execution."""
        
        if action == "connect":
            if not server_url:
                return ToolResult(False, "", "server_url required")
            return await self._connect(server_url, server_name or server_url)
        
        elif action == "disconnect":
            if not server_name:
                return ToolResult(False, "", "server_name required")
            return await self._disconnect(server_name)
        
        elif action == "list":
            return self._list_servers()
        
        elif action == "call":
            if not server_name or not tool_name:
                return ToolResult(False, "", "server_name and tool_name required")
            return await self._call_tool(server_name, tool_name, tool_args or {})
        
        return ToolResult(False, "", f"Unknown action: {action}")
    
    async def _connect(self, url: str, name: str) -> ToolResult:
        """Connect to an MCP server."""
        try:
            # Try HTTP-based MCP (simpler than WebSocket)
            import httpx
            
            # Get server manifest
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/manifest", timeout=10)
                
                if response.status_code == 200:
                    manifest = response.json()
                    
                    server = MCPServer(
                        name=name,
                        url=url,
                        tools=manifest.get("tools", []),
                        connected=True,
                    )
                    
                    self._servers[name] = server
                    
                    tool_names = [t.get("name", "unknown") for t in server.tools]
                    return ToolResult(
                        success=True,
                        output=f"Connected to {name}. Available tools: {', '.join(tool_names)}",
                        metadata={"tools": tool_names},
                    )
                else:
                    return ToolResult(
                        False, "",
                        f"Failed to connect: HTTP {response.status_code}",
                    )
                    
        except Exception as e:
            # Store as placeholder for manual configuration
            self._servers[name] = MCPServer(name=name, url=url, connected=False)
            return ToolResult(
                False, "",
                f"Could not auto-connect: {e}. Server registered for manual config.",
            )
    
    async def _disconnect(self, name: str) -> ToolResult:
        """Disconnect from an MCP server."""
        if name in self._servers:
            del self._servers[name]
            return ToolResult(True, f"Disconnected from {name}")
        return ToolResult(False, "", f"Server not found: {name}")
    
    def _list_servers(self) -> ToolResult:
        """List connected servers and their tools."""
        if not self._servers:
            return ToolResult(True, "No MCP servers connected")
        
        lines = []
        for name, server in self._servers.items():
            status = "✓" if server.connected else "✗"
            lines.append(f"{status} {name}: {server.url}")
            for tool in server.tools:
                lines.append(f"   - {tool.get('name', 'unknown')}")
        
        return ToolResult(
            True,
            "\n".join(lines),
            metadata={"servers": list(self._servers.keys())},
        )
    
    async def _call_tool(
        self,
        server_name: str,
        tool_name: str,
        args: Dict[str, Any],
    ) -> ToolResult:
        """Call a tool on an MCP server."""
        if server_name not in self._servers:
            return ToolResult(False, "", f"Server not found: {server_name}")
        
        server = self._servers[server_name]
        
        if not server.connected:
            return ToolResult(False, "", f"Server not connected: {server_name}")
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{server.url}/call",
                    json={"tool": tool_name, "args": args},
                    timeout=60,
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return ToolResult(
                        success=True,
                        output=json.dumps(result, indent=2),
                        metadata={"server": server_name, "tool": tool_name},
                    )
                else:
                    return ToolResult(
                        False, "",
                        f"Tool call failed: HTTP {response.status_code}",
                    )
                    
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    # Convenience methods
    def connect(self, url: str, name: Optional[str] = None) -> bool:
        """Connect to an MCP server."""
        result = self.execute("connect", server_url=url, server_name=name)
        return result.success
    
    def call(self, server: str, tool: str, **kwargs) -> Any:
        """Call a tool on a connected server."""
        result = self.execute("call", server_name=server, tool_name=tool, tool_args=kwargs)
        if result.success:
            return json.loads(result.output)
        raise RuntimeError(result.error)

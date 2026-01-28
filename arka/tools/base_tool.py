"""
ARKA Tool Base
Abstract base class for all tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import time


class ToolCategory(Enum):
    """Categories of tools."""
    SYSTEM = "system"
    WEB = "web"
    MEMORY = "memory"
    MCP = "mcp"


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for ARKA tools.
    All tools must implement execute() method.
    """
    
    # Override in subclasses
    NAME: str = "base_tool"
    DESCRIPTION: str = "Base tool"
    CATEGORY: ToolCategory = ToolCategory.SYSTEM
    REQUIRES_CONFIRMATION: bool = False
    
    def __init__(self):
        self.execution_count = 0
        self.last_result: Optional[ToolResult] = None
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Get the tool schema for LLM function calling."""
        return {
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "parameters": self.get_parameters(),
        }
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get parameter schema for this tool."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def __call__(self, **kwargs) -> ToolResult:
        """Execute the tool."""
        start = time.time()
        
        try:
            result = self.execute(**kwargs)
            result.duration = time.time() - start
        except Exception as e:
            result = ToolResult(
                success=False,
                output=None,
                error=str(e),
                duration=time.time() - start,
            )
        
        self.execution_count += 1
        self.last_result = result
        return result


class ToolRegistry:
    """Registry of available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool."""
        self._tools[tool.NAME] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all tools (for LLM function calling)."""
        return [tool.schema for tool in self._tools.values()]
    
    def by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get tools by category."""
        return [t for t in self._tools.values() if t.CATEGORY == category]


# Global registry
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry

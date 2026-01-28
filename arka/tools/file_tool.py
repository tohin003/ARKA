"""
ARKA File Tool
Read, write, and manipulate files safely.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil

from arka.tools.base_tool import BaseTool, ToolResult, ToolCategory


class FileTool(BaseTool):
    """
    File operations with safety checks.
    """
    
    NAME = "file"
    DESCRIPTION = "Read, write, and manipulate files"
    CATEGORY = ToolCategory.SYSTEM
    REQUIRES_CONFIRMATION = False
    
    def __init__(
        self,
        allowed_paths: Optional[List[str]] = None,
        max_file_size: int = 1_000_000,  # 1MB
    ):
        super().__init__()
        self.allowed_paths = [Path(p).resolve() for p in (allowed_paths or [])]
        self.max_file_size = max_file_size
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write", "append", "delete", "list", "exists", "mkdir"],
                    "description": "The file operation to perform",
                },
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (for write/append actions)",
                },
            },
            "required": ["action", "path"],
        }
    
    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        if not self.allowed_paths:
            return True  # No restrictions
        
        resolved = path.resolve()
        return any(
            resolved == allowed or allowed in resolved.parents
            for allowed in self.allowed_paths
        )
    
    def execute(
        self,
        action: str,
        path: str,
        content: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a file operation.
        
        Args:
            action: read, write, append, delete, list, exists, mkdir
            path: File or directory path
            content: Content for write/append
            
        Returns:
            ToolResult with operation result
        """
        file_path = Path(path).resolve()
        
        # Check path restrictions
        if not self._is_path_allowed(file_path):
            return ToolResult(
                success=False,
                output="",
                error=f"Path not allowed: {path}",
            )
        
        try:
            if action == "read":
                return self._read(file_path)
            elif action == "write":
                return self._write(file_path, content or "")
            elif action == "append":
                return self._append(file_path, content or "")
            elif action == "delete":
                return self._delete(file_path)
            elif action == "list":
                return self._list(file_path)
            elif action == "exists":
                return self._exists(file_path)
            elif action == "mkdir":
                return self._mkdir(file_path)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )
    
    def _read(self, path: Path) -> ToolResult:
        """Read file contents."""
        if not path.exists():
            return ToolResult(False, "", f"File not found: {path}")
        
        if not path.is_file():
            return ToolResult(False, "", f"Not a file: {path}")
        
        if path.stat().st_size > self.max_file_size:
            return ToolResult(False, "", f"File too large (max {self.max_file_size} bytes)")
        
        content = path.read_text()
        return ToolResult(True, content, metadata={"size": len(content)})
    
    def _write(self, path: Path, content: str) -> ToolResult:
        """Write content to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return ToolResult(True, f"Written {len(content)} bytes to {path}")
    
    def _append(self, path: Path, content: str) -> ToolResult:
        """Append content to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(content)
        return ToolResult(True, f"Appended {len(content)} bytes to {path}")
    
    def _delete(self, path: Path) -> ToolResult:
        """Delete file or directory."""
        if not path.exists():
            return ToolResult(False, "", f"Path not found: {path}")
        
        if path.is_file():
            path.unlink()
            return ToolResult(True, f"Deleted file: {path}")
        elif path.is_dir():
            shutil.rmtree(path)
            return ToolResult(True, f"Deleted directory: {path}")
        
        return ToolResult(False, "", f"Unknown path type: {path}")
    
    def _list(self, path: Path) -> ToolResult:
        """List directory contents."""
        if not path.exists():
            return ToolResult(False, "", f"Directory not found: {path}")
        
        if not path.is_dir():
            return ToolResult(False, "", f"Not a directory: {path}")
        
        items = []
        for item in sorted(path.iterdir()):
            prefix = "[D]" if item.is_dir() else "[F]"
            items.append(f"{prefix} {item.name}")
        
        return ToolResult(True, "\n".join(items), metadata={"count": len(items)})
    
    def _exists(self, path: Path) -> ToolResult:
        """Check if path exists."""
        exists = path.exists()
        path_type = "directory" if path.is_dir() else "file" if path.is_file() else "unknown"
        return ToolResult(True, str(exists), metadata={"exists": exists, "type": path_type})
    
    def _mkdir(self, path: Path) -> ToolResult:
        """Create directory."""
        path.mkdir(parents=True, exist_ok=True)
        return ToolResult(True, f"Created directory: {path}")
    
    # Convenience methods
    def read(self, path: str) -> str:
        """Read file and return contents."""
        result = self.execute("read", path)
        if result.success:
            return result.output
        raise FileNotFoundError(result.error)
    
    def write(self, path: str, content: str) -> bool:
        """Write content to file."""
        result = self.execute("write", path, content)
        return result.success

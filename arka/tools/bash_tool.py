"""
ARKA Bash Tool
Execute shell commands safely with whitelist and confirmation.
"""

import subprocess
import shlex
from typing import Dict, Any, List, Optional

from arka.tools.base_tool import BaseTool, ToolResult, ToolCategory


# Dangerous commands that require confirmation
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r",
    "sudo",
    "chmod 777",
    "mkfs",
    "dd if=",
    "> /dev/",
    ":(){ :|:& };:",  # Fork bomb
    "mv /* ",
    "wget ",
    "curl ",
]

# Commands that are always blocked
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    ":(){ :|:& };:",
]


class BashTool(BaseTool):
    """
    Execute shell commands with safety checks.
    """
    
    NAME = "bash"
    DESCRIPTION = "Execute a shell command and return the output"
    CATEGORY = ToolCategory.SYSTEM
    REQUIRES_CONFIRMATION = False  # Set per-command
    
    def __init__(
        self,
        timeout: int = 60,
        max_output_size: int = 10000,
        allowed_commands: Optional[List[str]] = None,
    ):
        super().__init__()
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.allowed_commands = allowed_commands
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 60)",
                },
            },
            "required": ["command"],
        }
    
    def is_dangerous(self, command: str) -> bool:
        """Check if command is potentially dangerous."""
        cmd_lower = command.lower()
        return any(pattern in cmd_lower for pattern in DANGEROUS_PATTERNS)
    
    def is_blocked(self, command: str) -> bool:
        """Check if command is completely blocked."""
        cmd_lower = command.lower().strip()
        return any(blocked in cmd_lower for blocked in BLOCKED_COMMANDS)
    
    def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """
        Execute a shell command.
        
        Args:
            command: Shell command to execute
            cwd: Working directory
            timeout: Command timeout
            
        Returns:
            ToolResult with stdout/stderr
        """
        # Block dangerous commands
        if self.is_blocked(command):
            return ToolResult(
                success=False,
                output="",
                error="This command is blocked for safety reasons.",
            )
        
        # Check whitelist if set
        if self.allowed_commands:
            cmd_base = command.split()[0] if command else ""
            if cmd_base not in self.allowed_commands:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command '{cmd_base}' not in allowed list.",
                )
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            # Truncate if too long
            if len(output) > self.max_output_size:
                output = output[:self.max_output_size] + "\n... (truncated)"
            
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error=result.stderr if result.returncode != 0 else None,
                metadata={
                    "return_code": result.returncode,
                    "command": command,
                },
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout or self.timeout} seconds",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=str(e),
            )
    
    def run(self, command: str, **kwargs) -> str:
        """Convenience method that returns just the output."""
        result = self.execute(command, **kwargs)
        if result.success:
            return result.output
        raise RuntimeError(result.error)

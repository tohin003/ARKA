
import subprocess
from typing import Dict, Any, Optional
from arka.tools.base_tool import BaseTool, ToolResult, ToolCategory

class AudioTool(BaseTool):
    """
    Control System Audio (Volume, Mute) on macOS.
    """
    
    NAME = "audio"
    DESCRIPTION = "Control system volume and mute status"
    CATEGORY = ToolCategory.SYSTEM
    REQUIRES_CONFIRMATION = False
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["set_volume", "get_volume", "mute", "unmute"],
                    "description": "Action to perform",
                },
                "level": {
                    "type": "integer",
                    "description": "Volume level (0-100) for set_volume",
                },
            },
            "required": ["action"],
        }
    
    def execute(self, action: str, level: Optional[int] = None) -> ToolResult:
        try:
            if action == "set_volume":
                if level is None:
                    return ToolResult(False, "", "Level (0-100) required for set_volume")
                # macOS volume is 0-100
                script = f"set volume output volume {level}"
                self._run_applescript(script)
                return ToolResult(True, f"Volume set to {level}%")
                
            elif action == "get_volume":
                script = "output volume of (get volume settings)"
                res = self._run_applescript(script)
                return ToolResult(True, f"Current Volume: {res}%")
                
            elif action == "mute":
                script = "set volume output muted true"
                self._run_applescript(script)
                return ToolResult(True, "System Muted")
                
            elif action == "unmute":
                script = "set volume output muted false"
                self._run_applescript(script)
                return ToolResult(True, "System Unmuted")
                
            else:
                return ToolResult(False, "", f"Unknown action: {action}")
                
        except Exception as e:
            return ToolResult(False, "", f"Audio Error: {str(e)}")
            
    def _run_applescript(self, script: str) -> str:
        """Run osascript."""
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()

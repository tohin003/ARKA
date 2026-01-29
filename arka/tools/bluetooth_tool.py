
import subprocess
import re
from typing import Dict, Any, List, Optional
from arka.tools.base_tool import BaseTool, ToolResult, ToolCategory

class BluetoothTool(BaseTool):
    """
    Manage Bluetooth settings and connections via 'blueutil'.
    Requires 'brew install blueutil'.
    """
    
    NAME = "bluetooth"
    DESCRIPTION = "Manage Bluetooth power and devices (connect/disconnect)"
    CATEGORY = ToolCategory.SYSTEM
    REQUIRES_CONFIRMATION = False
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "on", "off", "list", "connect", "disconnect"],
                    "description": "power (on/off), list paired devices, or connect/disconnect",
                },
                "device": {
                    "type": "string",
                    "description": "Device name or address (for connect/disconnect)",
                },
            },
            "required": ["action"],
        }
    
    def execute(self, action: str, device: Optional[str] = None) -> ToolResult:
        # Check binary
        try:
            subprocess.run(["blueutil", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ToolResult(False, "", "Generic 'blueutil' tool not found. Please install: brew install blueutil")

        try:
            if action == "status":
                res = subprocess.run(["blueutil", "--power"], capture_output=True, text=True)
                state = "ON" if "1" in res.stdout else "OFF"
                return ToolResult(True, f"Bluetooth Power: {state}")
                
            elif action == "on":
                subprocess.run(["blueutil", "--power", "1"], check=True)
                return ToolResult(True, "Bluetooth turned ON")
                
            elif action == "off":
                subprocess.run(["blueutil", "--power", "0"], check=True)
                return ToolResult(True, "Bluetooth turned OFF")
                
            elif action == "list":
                # List paired devices
                res = subprocess.run(["blueutil", "--paired"], capture_output=True, text=True)
                # Output format: "address", "name", (misc)
                # We clean it up for the LLM
                devices = []
                for line in res.stdout.strip().split("\n"):
                    if not line: continue
                    # Extract address (xx-xx-xx-xx-xx-xx) and name
                    parts = line.split('"')
                    if len(parts) >= 4:
                        addr = parts[1]
                        name = parts[3]
                        devices.append(f"- {name} [{addr}]")
                return ToolResult(True, "Paired Devices:\n" + "\n".join(devices))
                
            elif action in ["connect", "disconnect"]:
                if not device:
                    return ToolResult(False, "", f"Device name required for {action}")
                
                # Resolving Name to Address
                target_addr = self._resolve_device(device)
                if not target_addr:
                    return ToolResult(False, "", f"Device '{device}' not found in paired list.")
                
                cmd_flag = "--connect" if action == "connect" else "--disconnect"
                subprocess.run(["blueutil", cmd_flag, target_addr], check=True)
                
                # Check status
                res = subprocess.run(["blueutil", "--is-connected", target_addr], capture_output=True, text=True)
                success = "1" in res.stdout if action == "connect" else "0" in res.stdout
                
                if success:
                    return ToolResult(True, f"Successfully {action}ed '{device}'")
                else:
                    return ToolResult(False, "", f"Failed to {action} '{device}' (Start timeout?)")
                    
        except Exception as e:
            return ToolResult(False, "", f"Bluetooth Error: {str(e)}")
            
    def _resolve_device(self, query: str) -> Optional[str]:
        """Find MAC address by name."""
        try:
            res = subprocess.run(["blueutil", "--paired"], capture_output=True, text=True)
            for line in res.stdout.strip().split("\n"):
                if query.lower() in line.lower():
                    # Format: address-"xx-xx-xx-xx-xx-xx", name-"Device Name", ...
                    # blueutil output: address: 00-00-00-00-00-00, not connected, name: "Foo"
                    # Wait, verify format. `blueutil --paired` -> `address: 94-db-56-..., not connected, name: "AirPods"`
                    parts = line.split(",")
                    addr_part = parts[0]
                    if "address:" in addr_part:
                        addr = addr_part.split("address:")[1].strip()
                        return addr
        except:
            pass
        return None

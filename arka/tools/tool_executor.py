"""
ARKA Tool Executor
Connects LLM function calling to actual tool execution.
Full system access with enhanced app interaction.
"""

import json
import subprocess
from typing import Dict, Any, List, Optional

from arka.tools.system_controller import get_system_controller, SystemController


# Extended tool definitions for OpenAI function calling
from arka.core.computer_controller import get_computer_controller
from arka.core.browser_manager import get_browser_manager
from arka.vision.screen_analyzer import get_screen_analyzer

from arka.tools.core_defs import CORE_TOOL_DEFINITIONS
from arka.skills.registry import get_skill_registry


class ToolExecutor:
    """Executes tools based on LLM function calls."""
    
    def __init__(self):
        self.sys = get_system_controller()
        self.computer = get_computer_controller()
        self.browser = get_browser_manager()
        self.analyzer = get_screen_analyzer()
        self.registry = get_skill_registry()
    
    def get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for OpenAI API."""
        # 1. Core Tools
        tools = CORE_TOOL_DEFINITIONS.copy()
        
        # 2. Dynamic Skill Tools
        skill_tools = self.registry.get_all_tools()
        tools.extend(skill_tools)
        
        return tools
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        
        # 1. Check Dynamic Registry First
        skill_func = self.registry.get_tool_func(tool_name)
        if skill_func:
            try:
                # Skill tools might need access to system/browser
                # We can inject them if the function accepts them, 
                # or rely on the function using singletons (get_system_controller).
                # For now, simplistic execution:
                return str(skill_func(**arguments))
            except Exception as e:
                return f"Error executing skill tool '{tool_name}': {e}"

        # 2. Check Core Tools (Legacy Implementation)
        try:
            # Vision & Desktop
            if tool_name == "vision_click":
                query = arguments["query"]
                element = self.analyzer.find_element(query)
                if not element:
                    return f"Could not find element matching '{query}'"
                
                clicks = 2 if arguments.get("double_click") else 1
                self.computer.click(element.x, element.y, clicks=clicks)
                return f"Clicked '{query}' at ({element.x}, {element.y})"

            elif tool_name == "vision_analyze":
                return self.analyzer.analyze_screen_state(arguments["question"])
                
            # Web Browser
            elif tool_name == "web_navigate":
                self.browser.navigate(arguments["url"])
                return f"Navigated to {arguments['url']}"
                
            elif tool_name == "web_click":
                # Try simple selector first
                try:
                    self.browser.click(arguments["selector"])
                    return f"Clicked {arguments['selector']}"
                except Exception:
                    # Fallback strategies could go here (e.g. text match)
                    return f"Failed to click {arguments['selector']}"
                    
            elif tool_name == "web_type":
                self.browser.type_text(arguments["selector"], arguments["text"])
                return f"Typed '{arguments['text']}' into {arguments['selector']}"
                
            elif tool_name == "web_read":
                return self.browser.get_visible_text()[:2000]

            # App Control
            if tool_name == "open_application":
                result = self.sys.open_app(arguments["app_name"])
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "quit_application":
                from rich.prompt import Confirm
                from rich.console import Console
                # Minimal confirmation
                console = Console()
                console.print(f"[bold red]⚠️  Security Alert[/bold red]")
                console.print(f"Agent wants to QUIT application: [bold yellow]{arguments['app_name']}[/bold yellow]")
                if not Confirm.ask("Allow this?"):
                     return "Action blocked by user."
                
                result = self.sys.quit_app(arguments["app_name"])
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "get_running_apps":
                apps = self.sys.get_running_apps()
                return f"Running apps: {', '.join(apps)}"
            
            # Browser - YouTube search
            elif tool_name == "search_youtube":
                browser = arguments.get("browser", "default")
                result = self.sys.youtube_search_in_browser(arguments["query"], browser)
                return result.output if result.success else f"Error: {result.error}"

            # Bluetooth
            elif tool_name == "bluetooth":
                from arka.tools.bluetooth_tool import BluetoothTool
                tool = BluetoothTool()
                res = tool.execute(arguments["action"], arguments.get("device"))
                return res.output if res.success else f"Error: {res.error}"

            # Audio
            elif tool_name == "audio":
                from arka.tools.audio_tool import AudioTool
                tool = AudioTool()
                res = tool.execute(arguments["action"], arguments.get("level"))
                return res.output if res.success else f"Error: {res.error}"

            # Learned Skills
            elif tool_name == "execute_skill":
                from arka.skills.skill_forge import get_skill_forge
                forge = get_skill_forge()
                skill = forge.get(arguments["name"])
                if not skill:
                    return f"Error: Skill '{arguments['name']}' not found."
                    
                # Extract code from raw_response if available (for visual skills)
                if skill.metadata.get("raw_response"):
                    import re
                    # Extract applescript block
                    match = re.search(r"```applescript\n(.*?)\n```", skill.metadata["raw_response"], re.DOTALL)
                    if match:
                        code = match.group(1)
                        return self.sys._run_applescript(code).output or "Executed skill code."
                
                return f"Executed skill '{skill.name}'. Steps:\n" + "\n".join(skill.steps)
            
            elif tool_name == "open_url":
                browser = arguments.get("browser", "default")
                result = self.sys.open_url(arguments["url"], browser)
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "search_google":
                result = self.sys.search_google(arguments["query"])
                return result.output if result.success else f"Error: {result.error}"
            
            # Music - with search and play
            elif tool_name == "play_music":
                app = arguments.get("app", "music").lower()
                query = arguments["query"]
                if app == "spotify":
                    result = self.sys.spotify_search_and_play(query)
                else:
                    result = self.sys.music_search_and_play(query)
                return result.output if result.success else f"Error: {result.error}"
                return result.output if result.success else f"Error: {result.error}"
            
            # Memory Management
            elif tool_name in ["create_memory_node", "list_memory_nodes", "store_memory", "delete_memory_node"]:
                func = MEMORY_TOOLS[tool_name]
                # Filter args to match signature? Or just kwargs?
                # Usually simple kwargs for our tools
                return func(**arguments)

            # File System
            elif tool_name == "open_folder":
                result = self.sys.open_folder(arguments["path"])
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "read_file":
                import os
                path = os.path.expanduser(arguments["path"])
                with open(path, "r") as f:
                    return f.read()[:2000]
            
            elif tool_name == "write_file":
                from rich.prompt import Confirm
                from rich.console import Console
                import os
                path = os.path.expanduser(arguments["path"])
                
                console = Console()
                console.print(f"[bold red]⚠️  Security Alert[/bold red]")
                console.print(f"Agent wants to WRITE to file: [bold yellow]{path}[/bold yellow]")
                if os.path.exists(path):
                    console.print("[dim](File exists - will overwrite)[/dim]")
                
                if not Confirm.ask("Allow writing?"):
                    return "Action blocked by user."
                    
                with open(path, "w") as f:
                    f.write(arguments["content"])
                return f"Written to {path}"
            
            elif tool_name == "list_directory":
                import os
                path = os.path.expanduser(arguments["path"])
                items = os.listdir(path)
                return "\n".join(items[:50])
            
            # Shell
            # Shell
            elif tool_name == "run_shell":
                from arka.core.security import get_security_manager, SecurityLevel
                from rich.prompt import Confirm
                from rich.console import Console
                
                sec = get_security_manager()
                check = sec.check_command(arguments["command"])
                
                if check == SecurityLevel.BLOCKED:
                    return "Error: Command identified as destructive/blocked."
                
                if check == SecurityLevel.CONFIRMATION_REQUIRED:
                    # In a real agent loop, we might not have direct console access if it's headless,
                    # but since this is a CLI agent, we can use rich prompt.
                    console = Console()
                    console.print(f"[bold red]⚠️  Security Alert[/bold red]")
                    console.print(f"Agent wants to execute: [bold yellow]{arguments['command']}[/bold yellow]")
                    if not Confirm.ask("Allow this command?"):
                        return "Action blocked by user."
                
                result = self.sys.run_shell(arguments["command"])
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "run_in_terminal":
                from arka.core.security import get_security_manager, SecurityLevel
                from rich.prompt import Confirm
                from rich.console import Console

                sec = get_security_manager()
                check = sec.check_command(arguments["command"])
                
                if check == SecurityLevel.BLOCKED:
                     return "Error: Command identified as destructive/blocked."
                     
                if check == SecurityLevel.CONFIRMATION_REQUIRED:
                    console = Console()
                    console.print(f"[bold red]⚠️  Security Alert[/bold red]")
                    console.print(f"Agent wants to run in terminal: [bold yellow]{arguments['command']}[/bold yellow]")
                    if not Confirm.ask("Allow this command?"):
                        return "Action blocked by user."

                result = self.sys.terminal_run(arguments["command"])
                return result.output if result.success else f"Error: {result.error}"
            
            # Keyboard
            elif tool_name == "type_text":
                result = self.sys.type_via_clipboard(arguments["text"])
                return "Typed text" if result.success else f"Error: {result.error}"
            
            elif tool_name == "press_key":
                modifiers = arguments.get("modifiers", [])
                result = self.sys.press_key(arguments["key"], modifiers)
                return f"Pressed {arguments['key']}" if result.success else f"Error: {result.error}"
            
            # Clipboard
            elif tool_name == "get_clipboard":
                return self.sys.get_clipboard()
            
            elif tool_name == "set_clipboard":
                result = self.sys.set_clipboard(arguments["text"])
                return result.output
            
            # Notes/Reminders
            elif tool_name == "create_note":
                result = self.sys.notes_create(arguments["title"], arguments["body"])
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "create_reminder":
                result = self.sys.reminder_create(
                    arguments["title"],
                    arguments.get("due_date")
                )
                return result.output if result.success else f"Error: {result.error}"
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"Tool execution error: {str(e)}"


# Global executor
_executor: Optional[ToolExecutor] = None


def get_tool_executor() -> ToolExecutor:
    """Get or create global tool executor."""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor

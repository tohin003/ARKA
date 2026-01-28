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
TOOL_DEFINITIONS = [
    # ==================== App Control ====================
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open any macOS application (Safari, Chrome, Comet, Finder, Spotify, VS Code, Music, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to open"
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quit_application",
            "description": "Quit/close a running application",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to quit"
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_running_apps",
            "description": "Get list of currently running applications",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    
    # ==================== Browser ====================
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the default or specified browser",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to open"
                    },
                    "browser": {
                        "type": "string",
                        "description": "Browser name (Safari, Chrome, Comet, Firefox). Default: system default"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Search YouTube for a video and open in browser. Can specify browser like Comet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Video/song to search for"
                    },
                    "browser": {
                        "type": "string",
                        "description": "Browser to use (Comet, Safari, Chrome). Default: default browser"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_google",
            "description": "Search Google for a query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    
    # ==================== Skills ====================
    {
        "type": "function",
        "function": {
            "name": "execute_skill",
            "description": "Execute a learned skill by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the skill to execute"}
                },
                "required": ["name"]
            }
        }
    },

    # ==================== Music ====================
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Search for and play a song in Apple Music or Spotify. Opens the app, searches, and plays the song.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Song name, artist, or search query"
                    },
                    "app": {
                        "type": "string",
                        "description": "Music app: 'music' for Apple Music, 'spotify' for Spotify. Default: music"
                    }
                },
                "required": ["query"]
            }
        }
    },
    
    # ==================== File System ====================
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Open a folder in Finder",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the folder (supports ~ for home)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to directory"
                    }
                },
                "required": ["path"]
            }
        }
    },
    
    # ==================== Shell Commands ====================
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Execute a shell command and return output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_in_terminal",
            "description": "Open Terminal and run a command (visible to user)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to run in Terminal"
                    }
                },
                "required": ["command"]
            }
        }
    },
    
    # ==================== Keyboard ====================
    {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text at current cursor position in the active app",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to type"
                    }
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a keyboard key with optional modifiers",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Key: return, tab, escape, space, up, down, left, right, or letter"
                    },
                    "modifiers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Modifier keys: cmd, shift, alt, ctrl"
                    }
                },
                "required": ["key"]
            }
        }
    },
    
    # ==================== Clipboard ====================
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Get current clipboard contents",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_clipboard",
            "description": "Copy text to clipboard",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to copy"
                    }
                },
                "required": ["text"]
            }
        }
    },
    
    # ==================== Notes/Reminders ====================
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Create a note in Apple Notes",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Note title"
                    },
                    "body": {
                        "type": "string",
                        "description": "Note content"
                    }
                },
                "required": ["title", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a reminder in Apple Reminders",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Reminder title"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "Due date (optional)"
                    }
                },
                "required": ["title"]
            }
        }
    },
]


class ToolExecutor:
    """Executes tools based on LLM function calls."""
    
    def __init__(self):
        self.sys = get_system_controller()
    
    def get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions for OpenAI API."""
        return TOOL_DEFINITIONS
    
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        try:
            # App Control
            if tool_name == "open_application":
                result = self.sys.open_app(arguments["app_name"])
                return result.output if result.success else f"Error: {result.error}"
            
            elif tool_name == "quit_application":
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
                import os
                path = os.path.expanduser(arguments["path"])
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

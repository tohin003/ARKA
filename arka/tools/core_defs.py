"""
Core Tool Definitions for ARKA.
These are the built-in tools (Browser, System, Vision, Memory) that are always available.
"""

CORE_TOOL_DEFINITIONS = [
    # ==================== Memory Management ====================
    {
        "type": "function",
        "function": {
            "name": "create_memory_node",
            "description": "Create a new memory node/category (e.g. 'project_x')",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the node"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_memory_nodes",
            "description": "List all active memory nodes",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_memory",
            "description": "Store info in a specific node (also auto-saves to 'general')",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Information to store"},
                    "node": {"type": "string", "description": "Target node name (default: 'general')"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory_node",
            "description": "Delete a memory node and all its contents",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of node to delete"}
                },
                "required": ["name"]
            }
        }
    },
    # ==================== System Tools ====================
    {
        "type": "function",
        "function": {
            "name": "bluetooth",
            "description": "Manage Bluetooth (power on/off, connect devices)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "on", "off", "list", "connect", "disconnect"],
                        "description": "Action: status, on, off, list, connect, disconnect"
                    },
                    "device": {
                        "type": "string",
                        "description": "Device name or address (for connect/disconnect)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "audio",
            "description": "Control system audio (volume, mute)",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["set_volume", "get_volume", "mute", "unmute"],
                        "description": "Action: set_volume, get_volume, mute, unmute"
                    },
                    "level": {
                        "type": "integer",
                        "description": "Volume level (0-100)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    # ==================== Vision & Desktop GUI ====================
    {
        "type": "function",
        "function": {
            "name": "vision_click",
            "description": "Find a UI element by description and click it (e.g. 'Play button')",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Description of element to click"},
                    "double_click": {"type": "boolean", "description": "True for double click"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vision_analyze",
            "description": "Analyze the screen state to answer a question",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question about screen state"}
                },
                "required": ["question"]
            }
        }
    },
    
    # ==================== Web Browser (Playwright) ====================
    {
        "type": "function",
        "function": {
            "name": "web_navigate",
            "description": "Navigate to a URL in Chrome",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to visit"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_click",
            "description": "Click an element on the web page using a CSS selector or text",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector or text content"}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_type",
            "description": "Type text into a web element",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector"},
                    "text": {"type": "string", "description": "Text to type"}
                },
                "required": ["selector", "text"]
            }
        }
    },
     {
        "type": "function",
        "function": {
            "name": "web_read",
            "description": "Get the text content of the current page",
            "parameters": {"type": "object", "properties": {}}
        }
    },

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
            "description": "Execute a learned skill by name (Legacy SkillForge).",
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
            "description": "Type text at current cursor position in the active active app",
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

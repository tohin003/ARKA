"""
ARKA System Controller
Full macOS system access via AppleScript and shell commands.
Enhanced with app interaction, typing, and search capabilities.
"""

import subprocess
import os
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ActionResult:
    """Result of a system action."""
    success: bool
    output: str
    error: Optional[str] = None


class SystemController:
    """
    Full system access controller for macOS.
    Uses AppleScript for GUI automation and shell for system commands.
    """
    
    def __init__(self):
        self.last_app: Optional[str] = None
    
    # ==================== App Control ====================
    
    def open_app(self, app_name: str) -> ActionResult:
        """Open any macOS application."""
        try:
            subprocess.run(["open", "-a", app_name], check=True)
            self.last_app = app_name
            time.sleep(0.5)  # Wait for app to open
            return ActionResult(True, f"Opened {app_name}")
        except subprocess.CalledProcessError as e:
            return ActionResult(False, "", f"Failed to open {app_name}: {e}")
    
    def quit_app(self, app_name: str) -> ActionResult:
        """Quit an application."""
        script = f'tell application "{app_name}" to quit'
        return self._run_applescript(script)
    
    def get_running_apps(self) -> List[str]:
        """Get list of running applications."""
        script = '''
        tell application "System Events"
            set appList to name of every process whose background only is false
        end tell
        return appList
        '''
        result = self._run_applescript(script)
        if result.success:
            return [app.strip() for app in result.output.split(",")]
        return []
    
    def get_frontmost_app(self) -> str:
        """Get the currently focused application."""
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
        end tell
        return frontApp
        '''
        result = self._run_applescript(script)
        return result.output.strip() if result.success else ""
    
    def bring_to_front(self, app_name: str) -> ActionResult:
        """Bring an app to the front."""
        script = f'tell application "{app_name}" to activate'
        return self._run_applescript(script)
    
    # ==================== Browser Control ====================
    
    def open_url(self, url: str, browser: str = "default") -> ActionResult:
        """Open URL in browser."""
        if browser == "default":
            subprocess.run(["open", url], check=True)
            return ActionResult(True, f"Opened {url}")
        else:
            subprocess.run(["open", "-a", browser, url], check=True)
            return ActionResult(True, f"Opened {url} in {browser}")
    
    def search_google(self, query: str) -> ActionResult:
        """Search Google."""
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self.open_url(url)
    
    def search_youtube(self, query: str, browser: str = "default") -> ActionResult:
        """Search YouTube and open in specified browser."""
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        if browser != "default":
            subprocess.run(["open", "-a", browser, url], check=True)
            return ActionResult(True, f"Opened YouTube search for '{query}' in {browser}")
        else:
            subprocess.run(["open", url], check=True)
            return ActionResult(True, f"Opened YouTube search for '{query}'")
    
    def new_browser_tab(self, browser: str = "Safari") -> ActionResult:
        """Open new tab in browser."""
        script = f'''
        tell application "{browser}"
            activate
            delay 0.3
        end tell
        tell application "System Events"
            keystroke "t" using command down
        end tell
        '''
        return self._run_applescript(script)
    
    def browser_type_and_search(self, query: str, browser: str = "Safari") -> ActionResult:
        """Open browser, type in search bar, and search."""
        script = f'''
        tell application "{browser}"
            activate
            delay 0.5
        end tell
        tell application "System Events"
            -- Open new tab
            keystroke "t" using command down
            delay 0.3
            -- Focus URL bar
            keystroke "l" using command down
            delay 0.2
            -- Type the URL
            keystroke "https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            delay 0.2
            -- Press enter
            keystroke return
        end tell
        '''
        return self._run_applescript(script)
    
    # ==================== Finder Control ====================
    
    def open_folder(self, path: str) -> ActionResult:
        """Open folder in Finder."""
        expanded = os.path.expanduser(path)
        subprocess.run(["open", expanded], check=True)
        return ActionResult(True, f"Opened {path}")
    
    def get_selected_files(self) -> List[str]:
        """Get currently selected files in Finder."""
        script = '''
        tell application "Finder"
            set selectedItems to selection
            set pathList to {}
            repeat with anItem in selectedItems
                set end of pathList to POSIX path of (anItem as text)
            end repeat
        end tell
        return pathList
        '''
        result = self._run_applescript(script)
        if result.success:
            return [f.strip() for f in result.output.split(",") if f.strip()]
        return []
    
    # ==================== Keyboard/Mouse ====================
    
    def type_text(self, text: str, delay: float = 0.05) -> ActionResult:
        """Type text at current cursor position."""
        # Escape special characters for AppleScript
        escaped = text.replace('\\', '\\\\').replace('"', '\\"')
        script = f'''
        tell application "System Events"
            keystroke "{escaped}"
        end tell
        '''
        return self._run_applescript(script)
    
    def type_text_slow(self, text: str) -> ActionResult:
        """Type text character by character (more reliable)."""
        script = f'''
        tell application "System Events"
            repeat with c in characters of "{text}"
                keystroke c
                delay 0.03
            end repeat
        end tell
        '''
        return self._run_applescript(script)
    
    def press_key(self, key: str, modifiers: List[str] = None) -> ActionResult:
        """Press a keyboard key with optional modifiers."""
        mod_str = ""
        if modifiers:
            mod_map = {
                "cmd": "command down",
                "command": "command down",
                "shift": "shift down",
                "alt": "option down",
                "option": "option down",
                "ctrl": "control down",
                "control": "control down"
            }
            mods = [mod_map.get(m.lower(), m) for m in modifiers]
            mod_str = f" using {{{', '.join(mods)}}}"
        
        # Handle special keys
        if key.lower() in ["return", "enter"]:
            script = f'tell application "System Events" to keystroke return{mod_str}'
        elif key.lower() == "tab":
            script = f'tell application "System Events" to keystroke tab{mod_str}'
        elif key.lower() == "escape":
            script = f'tell application "System Events" to key code 53{mod_str}'
        elif key.lower() == "space":
            script = f'tell application "System Events" to keystroke " "{mod_str}'
        elif key.lower() in ["up", "down", "left", "right"]:
            key_codes = {"up": 126, "down": 125, "left": 123, "right": 124}
            script = f'tell application "System Events" to key code {key_codes[key.lower()]}{mod_str}'
        else:
            script = f'tell application "System Events" to keystroke "{key}"{mod_str}'
        
        return self._run_applescript(script)
    
    def click_at(self, x: int, y: int) -> ActionResult:
        """Click at screen coordinates using cliclick if available."""
        try:
            # Try cliclick first (more reliable)
            subprocess.run(["cliclick", f"c:{x},{y}"], check=True)
            return ActionResult(True, f"Clicked at ({x}, {y})")
        except:
            # Fallback to AppleScript
            script = f'''
            tell application "System Events"
                click at {{{x}, {y}}}
            end tell
            '''
            return self._run_applescript(script)
    
    # ==================== Clipboard ====================
    
    def get_clipboard(self) -> str:
        """Get clipboard contents."""
        result = subprocess.run(["pbpaste"], capture_output=True, text=True)
        return result.stdout
    
    def set_clipboard(self, text: str) -> ActionResult:
        """Set clipboard contents."""
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(text.encode())
        return ActionResult(True, "Clipboard updated")
    
    def paste_from_clipboard(self) -> ActionResult:
        """Paste clipboard contents."""
        script = '''
        tell application "System Events"
            keystroke "v" using command down
        end tell
        '''
        return self._run_applescript(script)
    
    def type_via_clipboard(self, text: str) -> ActionResult:
        """Type text by copying to clipboard and pasting (most reliable)."""
        self.set_clipboard(text)
        time.sleep(0.1)
        return self.paste_from_clipboard()
    
    def get_screen_size(self) -> tuple:
        """Get screen dimensions."""
        script = '''
        tell application "Finder"
            set screenBounds to bounds of window of desktop
        end tell
        return screenBounds
        '''
        result = self._run_applescript(script)
        if result.success:
            parts = result.output.split(",")
            if len(parts) >= 4:
                return (int(parts[2].strip()), int(parts[3].strip()))
        return (1920, 1080)  # Default
    
    def run_shell(self, command: str) -> ActionResult:
        """Run shell command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return ActionResult(True, result.stdout)
            else:
                return ActionResult(False, result.stdout, result.stderr)
        except Exception as e:
            return ActionResult(False, "", str(e))
    
    # ==================== App-Specific Actions ====================
    
    def music_search_and_play(self, query: str) -> ActionResult:
        """Open Apple Music, search for a song, and play it."""
        script = f'''
        tell application "Music"
            activate
        end tell
        delay 1.0
        tell application "System Events"
            tell process "Music"
                -- Active search
                keystroke "f" using command down
                delay 0.5
                keystroke "a" using command down
                keystroke "{query}"
                delay 0.8
                keystroke return
                delay 1.5
                
                -- Navigate to results area (Tab usually moves focus from search to results)
                keystroke tab
                delay 0.2
                -- Select first item in list
                keystroke down
                delay 0.2
                keystroke return
                delay 1.0
                
                -- Now try to play
                try
                    -- Search for Play button in the new view
                    click (first button whose description contains "Play" or name contains "Play") of window 1
                on error
                    -- Fallback: Press Space
                    keystroke space
                end try
            end tell
        end tell
        '''
        return self._run_applescript(script)
    
    def spotify_search_and_play(self, query: str) -> ActionResult:
        """Open Spotify, search, and play."""
        script = f'''
        tell application "Spotify"
            activate
        end tell
        delay 1
        tell application "System Events"
            tell process "Spotify"
                -- Open search (Cmd+L or Cmd+K)
                keystroke "l" using command down
                delay 0.3
                -- Type query
                keystroke "{query}"
                delay 0.5
                keystroke return
                delay 1.5
                keystroke return
            end tell
        end tell
        '''
        return self._run_applescript(script)
    
    def youtube_search_in_browser(self, query: str, browser: str = "Comet") -> ActionResult:
        """Open browser, go to YouTube, and search for video."""
        # First open the browser with YouTube search URL directly
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        try:
            subprocess.run(["open", "-a", browser, url], check=True)
            return ActionResult(True, f"Opened YouTube search for '{query}' in {browser}")
        except:
            # Fallback: open in default browser
            subprocess.run(["open", url], check=True)
            return ActionResult(True, f"Opened YouTube search for '{query}'")
    
    def notes_create(self, title: str, body: str) -> ActionResult:
        """Create a note in Notes app."""
        script = f'''
        tell application "Notes"
            activate
            make new note with properties {{name:"{title}", body:"{body}"}}
        end tell
        '''
        return self._run_applescript(script)
    
    def reminder_create(self, title: str, due_date: str = None) -> ActionResult:
        """Create a reminder."""
        if due_date:
            script = f'''
            tell application "Reminders"
                make new reminder with properties {{name:"{title}", due date:date "{due_date}"}}
            end tell
            '''
        else:
            script = f'''
            tell application "Reminders"
                make new reminder with properties {{name:"{title}"}}
            end tell
            '''
        return self._run_applescript(script)
    
    def terminal_run(self, command: str) -> ActionResult:
        """Run command in Terminal."""
        script = f'''
        tell application "Terminal"
            activate
            do script "{command}"
        end tell
        '''
        return self._run_applescript(script)
    
    # ==================== Helper ====================
    
    def _run_applescript(self, script: str) -> ActionResult:
        """Execute AppleScript."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return ActionResult(True, result.stdout.strip())
            else:
                return ActionResult(False, "", result.stderr.strip())
        except subprocess.TimeoutExpired:
            return ActionResult(False, "", "Script timed out")
        except Exception as e:
            return ActionResult(False, "", str(e))


# Global instance
_controller: Optional[SystemController] = None


def get_system_controller() -> SystemController:
    """Get or create global system controller."""
    global _controller
    if _controller is None:
        _controller = SystemController()
    return _controller

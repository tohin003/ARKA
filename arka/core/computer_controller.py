"""
ARKA Computer Controller
Global interface for mouse, keyboard, and screen interaction.
Wraps pyautogui and system commands.
"""

import time
import subprocess
import base64
import io
from typing import Tuple, Dict, Optional, List
from pathlib import Path

try:
    import pyautogui
    # Fail-safe: moving mouse to corner throws exception
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5  # Add delay between actions
except ImportError:
    pyautogui = None

from PIL import Image


class ComputerController:
    """
    Controls the computer's input devices and screen.
    """
    
    def __init__(self):
        if not pyautogui:
            raise ImportError("pyautogui not installed. Run 'pip install pyautogui'")
        
        self.screen_width, self.screen_height = pyautogui.size()
        
    def get_screen_size(self) -> Tuple[int, int]:
        """Get total screen size."""
        return (self.screen_width, self.screen_height)
    
    def screenshot(self, filename: Optional[str] = None) -> Image.Image:
        """Capture full screen and optionally save to file."""
        img = pyautogui.screenshot()
        if filename:
            img.save(filename)
        return img
    
    def get_screenshot_base64(self, resize_ratio: float = 1.0) -> str:
        """Get screenshot as base64 string for LLM."""
        img = self.screenshot()
        
        # Convert RGBA to RGB (JPEG doesn't support alpha)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        if resize_ratio != 1.0:
            w, h = img.size
            img = img.resize((int(w * resize_ratio), int(h * resize_ratio)))
            
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        return base64.b64encode(buffered.getvalue()).decode()
    
    def click(self, x: int, y: int, clicks: int = 1, interval: float = 0.0):
        """Click at specific coordinates."""
        # Sanity check coordinates
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))
        
        pyautogui.click(x, y, clicks=clicks, interval=interval)
        
    def type_text(self, text: str, interval: float = 0.05):
        """Type text with keyboard."""
        pyautogui.write(text, interval=interval)
        
    def press_key(self, key: str, modifiers: List[str] = None):
        """Press a key combination."""
        keys = (modifiers or []) + [key]
        pyautogui.hotkey(*keys)
        
    def scroll(self, clicks: int):
        """Scroll vertical."""
        pyautogui.scroll(clicks)

    def get_active_app(self) -> str:
        """Get name of the currently active application (macOS specific)."""
        script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        try:
            result = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.STDOUT)
            return result.decode('utf-8').strip()
        except Exception:
            return "Unknown"

    def open_app(self, app_name: str) -> bool:
        """Open or focus an application with smart name resolution."""
        # Try exact name first
        variations = [
            app_name,
            app_name.replace(" Browser", ""),  # "Comet Browser" -> "Comet"
            app_name.replace("Browser", "").strip(),
            app_name.split()[0] if " " in app_name else app_name,  # First word
        ]
        
        for name in variations:
            result = subprocess.run(
                ['open', '-a', name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                time.sleep(1)  # Wait for focus
                return True
        
        # Last resort: try to find in /Applications
        try:
            apps = subprocess.check_output(
                ['ls', '/Applications'],
                text=True
            ).split('\n')
            
            for app in apps:
                if app_name.lower().replace(" ", "") in app.lower().replace(" ", ""):
                    result = subprocess.run(['open', '-a', app.replace('.app', '')], capture_output=True)
                    if result.returncode == 0:
                        time.sleep(1)
                        return True
        except Exception:
            pass
        
        return False

    def run_applescript(self, script: str) -> str:
        """Run raw AppleScript."""
        try:
            result = subprocess.check_output(['osascript', '-e', script], stderr=subprocess.STDOUT)
            return result.decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            return f"Error: {e.output.decode('utf-8')}"


# Global instance
_controller = None

def get_computer_controller() -> ComputerController:
    global _controller
    if _controller is None:
        _controller = ComputerController()
    return _controller

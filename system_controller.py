import pyautogui
import subprocess
import time
import platform

class SystemController:
    """
    Universal System Controller - The "Hands" of the Agent.
    Can interact with ANY application on macOS.
    """
    def __init__(self):
        self.os_type = platform.system()
        # Safety: Move mouse to corner to abort
        pyautogui.FAILSAFE = True
        # Small delay for human-like interaction
        pyautogui.PAUSE = 0.05

    # ========== APP CONTROL ==========
    def get_frontmost_app(self):
        """Get the name of the currently active application."""
        if self.os_type == "Darwin":
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            try:
                return subprocess.check_output(["osascript", "-e", script]).decode().strip()
            except:
                return None
        return None

    def focus_app(self, app_name):
        """Bring an application to the front."""
        if self.os_type == "Darwin":
            script = f'tell application "{app_name}" to activate'
            subprocess.run(["osascript", "-e", script])
            time.sleep(0.3)

    # ========== INPUT CONTROL ==========
    def click(self, x, y, clicks=1, button='left'):
        """Click at coordinates."""
        pyautogui.click(x, y, clicks=clicks, button=button)

    def double_click(self, x, y):
        """Double click at coordinates."""
        pyautogui.doubleClick(x, y)

    def right_click(self, x, y):
        """Right click at coordinates."""
        pyautogui.rightClick(x, y)

    def move_to(self, x, y, duration=0.2):
        """Move mouse to coordinates."""
        pyautogui.moveTo(x, y, duration=duration)

    def drag_to(self, x, y, duration=0.5):
        """Drag from current position to coordinates."""
        pyautogui.drag(x - pyautogui.position()[0], y - pyautogui.position()[1], duration=duration)

    def scroll(self, amount):
        """Scroll up (positive) or down (negative)."""
        pyautogui.scroll(amount)

    def type_text(self, text, interval=0.02):
        """Type text character by character."""
        pyautogui.write(text, interval=interval)

    def type_unicode(self, text):
        """Type unicode text (for non-ASCII characters)."""
        # pyautogui.write() doesn't handle unicode well, use clipboard
        self.copy_to_clipboard(text)
        self.hotkey('command', 'v')

    def press_key(self, key):
        """Press a single key."""
        pyautogui.press(key)

    def hotkey(self, *keys):
        """Press a combination of keys (e.g., cmd+c)."""
        pyautogui.hotkey(*keys)

    # ========== CLIPBOARD ==========
    def copy_to_clipboard(self, text):
        """Copy text to system clipboard."""
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))

    def get_clipboard(self):
        """Get text from system clipboard."""
        return subprocess.check_output(['pbpaste']).decode('utf-8')

    def select_all_and_copy(self):
        """Cmd+A, Cmd+C to get current content."""
        self.hotkey('command', 'a')
        time.sleep(0.1)
        self.hotkey('command', 'c')
        time.sleep(0.1)
        return self.get_clipboard()

    # ========== UTILITY ==========
    def get_screen_size(self):
        """Get screen dimensions."""
        return pyautogui.size()

    def get_mouse_position(self):
        """Get current mouse position."""
        return pyautogui.position()

    def notify_user(self, title, message):
        """Send a macOS notification."""
        if self.os_type == "Darwin":
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script])

if __name__ == "__main__":
    ctrl = SystemController()
    print(f"Frontmost App: {ctrl.get_frontmost_app()}")
    print(f"Screen Size: {ctrl.get_screen_size()}")
    print(f"Mouse Position: {ctrl.get_mouse_position()}")
    ctrl.notify_user("Agent", "System Controller Initialized!")

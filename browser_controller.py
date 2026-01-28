import pyautogui
import platform
import subprocess
import time

class BrowserController:
    """
    Controls the ACTIVE browser window using System Events (AppleScript) and PyAutoGUI.
    Used for 'Instant Assist' on existing tabs.
    """
    def __init__(self):
        self.os_type = platform.system()
    
    def get_active_url(self):
        """
        MacOS only: Uses AppleScript to get the URL of the frontmost Chrome/Brave/Comet window.
        """
        if self.os_type == "Darwin":
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
            end tell
            
            if frontApp is "Google Chrome" or frontApp is "Brave Browser" or frontApp is "Comet" then
                tell application frontApp
                    return URL of active tab of front window
                end tell
            else
                return "Not a supported browser"
            end if
            '''
            try:
                result = subprocess.check_output(["osascript", "-e", script]).decode().strip()
                return result
            except Exception as e:
                print(f"Error getting URL: {e}")
                return None
        return None

    def type_text(self, text, interval=0.01):
        """
        Types text into the active field.
        """
        # Safety: Fail-safe if mouse hits corner
        pyautogui.FAILSAFE = True
        pyautogui.write(text, interval=interval)

    def select_all_and_copy(self):
        """
        Cmd+A, Cmd+C to get context.
        """
        pyautogui.hotkey('command', 'a')
        time.sleep(0.1)
        pyautogui.hotkey('command', 'c')
        time.sleep(0.1)
        # Read clipboard (requires pbpaste on mac)
        return subprocess.check_output("pbpaste").decode()

    def replace_selection(self, new_text):
        """
        Overwrites selected text with new_text.
        """
        self.type_text(new_text)

if __name__ == "__main__":
    # Test
    ctrl = BrowserController()
    print("Focus a browser window in 3 seconds...")
    time.sleep(3)
    url = ctrl.get_active_url()
    print(f"Detected URL: {url}")
    # ctrl.type_text("Hello derived from Instant Assist!")

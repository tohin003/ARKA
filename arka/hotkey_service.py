"""
ARKA Global Hotkey Service
Listens for Cmd+B to instantly invoke ARKA.
Uses pynput for cross-platform keyboard monitoring.
"""

import os
import sys
import time
import threading
import subprocess
from typing import Callable, Optional

# Check if pynput is available
try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard = None
    Key = None
    KeyCode = None


class HotkeyService:
    """
    Global hotkey listener for ARKA.
    
    Default hotkey: Cmd+B
    """
    
    def __init__(self):
        self.listener: Optional[keyboard.GlobalHotKeys] = None
        self.running = False
        self.ui_process: Optional[subprocess.Popen] = None
        
    def _on_hotkey(self):
        """Handle hotkey press - Launch Spotlight UI."""
        
        # Check if UI is already running
        if self.ui_process:
            if self.ui_process.poll() is None:
                print("⚠️  Spotlight UI is already open.")
                return
            else:
                self.ui_process = None
        
        print("\n🔥 Hotkey triggered! Launching Spotlight...")
        
        try:
            # Run as module to preserve sys.path and package structure
            self.ui_process = subprocess.Popen([sys.executable, "-m", "arka.ui.spotlight_ui"])
        except Exception as e:
            print(f"Failed to launch UI: {e}")

    def stop(self):
        """Stop listening for hotkeys."""
        if self.listener and self.running:
            self.listener.stop()
            self.running = False
            print("Hotkey service stopped.")
    
    def _run_listener(self):
        """Start the global hotkey listener non-blocking."""
        if not PYNPUT_AVAILABLE:
            print("Warning: pynput not installed. Hotkey service unavailable.")
            return False

        try:
            # Create listener but don't join it yet
            self.listener = keyboard.GlobalHotKeys({
                '<cmd>+b': self._on_hotkey
            })
            self.listener.start()
            self.running = True
            print("✓ Hotkey service started (Cmd+B).")
            return True
        except Exception as e:
            print(f"Failed to start hotkey service: {e}")
            return False

    def run_blocking(self):
        """Run the hotkey listener in blocking mode with a clean sleep loop."""
        print("Listening for Cmd+B... (Press Ctrl+C to stop)")
        
        if self._run_listener():
            try:
                # Keep main thread alive and responsive to signals
                while self.running and self.listener.is_alive():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nReceived signal, stopping...")
            finally:
                self.stop()
        else:
            print("Could not start listener.")

def start_hotkey_daemon():
    """Start hotkey service as a background daemon."""
    service = HotkeyService()
    thread = threading.Thread(target=service.run_blocking, daemon=True)
    thread.start()
    return service


def install_launch_agent():
    """Install a macOS LaunchAgent to run hotkey service at login."""
    plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.arka.hotkey</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-m</string>
        <string>arka.hotkey_service</string>
        <string>--daemon</string>
    </array>
    <key>WorkingDirectory</key>
    <string>''' + os.path.expanduser("~/Documents/DESKTOP/AI_AGENT-V1") + '''</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
'''
    
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.arka.hotkey.plist")
    with open(plist_path, "w") as f:
        f.write(plist_content)
    
    # Load the agent
    subprocess.run(["launchctl", "load", plist_path])
    print(f"✓ LaunchAgent installed at {plist_path}")
    print("  ARKA hotkey (Cmd+B) will now work system-wide.")


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="ARKA Hotkey Service")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--install", action="store_true", help="Install launch agent")
    args = parser.parse_args()
    
    if args.install:
        install_launch_agent()
    else:
        service = HotkeyService()
        service.run_blocking()


if __name__ == "__main__":
    main()

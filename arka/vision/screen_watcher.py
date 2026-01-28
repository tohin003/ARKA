"""
ARKA Screen Watcher
Captures screen content for visual learning.
Uses native macOS screencapture utility.
"""

import subprocess
import time
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class ScreenWatcher:
    """
    Captures screen content for visual analysis.
    """
    
    def __init__(self, capture_dir: Optional[Path] = None):
        self.capture_dir = capture_dir or Path.home() / ".arka" / "vision" / "captures"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[str] = None
        self._frames: List[Dict[str, str]] = []  # List of {path, timestamp}
    
    def start_session(self, session_name: str = None):
        """Start a new capture session."""
        timestamp = int(time.time())
        self.current_session = session_name or f"session_{timestamp}"
        self._frames = []
        
        # Create session directory
        session_dir = self.capture_dir / self.current_session
        session_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_frame(self) -> Optional[str]:
        """
        Capture a single frame (screenshot).
        Returns the path to the captured file.
        """
        if not self.current_session:
            self.start_session()
            
        timestamp = datetime.now().strftime("%H-%M-%S-%f")
        filename = f"frame_{timestamp}.jpg"
        path = self.capture_dir / self.current_session / filename
        
        # Use screencapture (macOS native)
        # -x: no sound
        # -r: do not capture shadow
        # -t jpg: format
        try:
            subprocess.run(
                ["screencapture", "-x", "-r", "-t", "jpg", str(path)],
                check=True,
                timeout=5
            )
            
            self._frames.append({
                "path": str(path),
                "timestamp": timestamp
            })
            return str(path)
        except Exception as e:
            print(f"Failed to capture frame: {e}")
            return None
    
    def get_frames(self) -> List[Dict[str, str]]:
        """Get all frames in current session."""
        return self._frames
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for LLM API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def clear_session(self):
        """Clear current session data (files remain on disk)."""
        self.current_session = None
        self._frames = []


# Global instance
_watcher: Optional[ScreenWatcher] = None


def get_screen_watcher() -> ScreenWatcher:
    """Get or create global screen watcher."""
    global _watcher
    if _watcher is None:
        _watcher = ScreenWatcher()
    return _watcher

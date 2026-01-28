import subprocess
import os
from datetime import datetime

try:
    from PIL import Image
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

class ScreenIntelligence:
    """
    Screen Intelligence - The "Eyes" of the Agent.
    Captures and analyzes the current screen state.
    """
    def __init__(self, screenshots_dir="screenshots"):
        self.screenshots_dir = screenshots_dir
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

    def capture_screen(self, save=True):
        """
        Capture the entire screen.
        Returns: PIL Image object and optionally saves to disk.
        """
        if HAS_MSS:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                if save:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = os.path.join(self.screenshots_dir, f"screen_{timestamp}.png")
                    img.save(path)
                    return img, path
                return img, None
        else:
            # Fallback: Use macOS screencapture
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.screenshots_dir, f"screen_{timestamp}.png")
            subprocess.run(["screencapture", "-x", path])
            return None, path

    def capture_active_window(self, save=True):
        """
        Capture only the active window (macOS).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.screenshots_dir, f"window_{timestamp}.png")
        # -l flag gets window by ID, -w captures interactive window
        subprocess.run(["screencapture", "-x", "-w", path])
        
        if os.path.exists(path):
            if HAS_MSS:
                img = Image.open(path)
                return img, path
            return None, path
        return None, None

    def get_screen_text_ocr(self, image_path):
        """
        Extract text from screenshot using OCR.
        Requires: tesseract installed (`brew install tesseract`)
        """
        try:
            result = subprocess.check_output(["tesseract", image_path, "stdout"]).decode()
            return result
        except Exception as e:
            print(f"OCR Error: {e}")
            return None

    def analyze_with_vision_model(self, image_path, prompt="Describe what you see on this screen."):
        """
        Analyze screen using a Vision Language Model (VLM).
        This is a placeholder - integration with Qwen-VL or similar needed.
        """
        # TODO: Integrate with Ollama's vision models (e.g., llava, bakllava)
        # Example: ollama run llava "Describe this image" < image_path
        print(f"[VLM] Would analyze: {image_path}")
        print(f"[VLM] Prompt: {prompt}")
        return "VLM analysis not yet implemented."

if __name__ == "__main__":
    si = ScreenIntelligence()
    print("Capturing screen in 2 seconds...")
    import time
    time.sleep(2)
    img, path = si.capture_screen()
    print(f"Screenshot saved: {path}")
    
    # Test OCR if tesseract is available
    # text = si.get_screen_text_ocr(path)
    # print(f"OCR Text (truncated): {text[:500] if text else 'N/A'}")

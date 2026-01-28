"""
ARKA Screen Analyzer
Visual intelligence module for locating UI elements on screen.
Uses GPT-4o to analyze screenshots and return click coordinates.
"""

import json
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

from arka.core.model_router import ModelRouter
from arka.core.computer_controller import get_computer_controller

@dataclass
class UIElement:
    x: int
    y: int
    label: str
    confidence: float # 0.0 to 1.0

class ScreenAnalyzer:
    """
    Analyzes screen content to find UI elements.
    """
    
    def __init__(self):
        self.router = ModelRouter()
        self.computer = get_computer_controller()
        
    def find_element(self, query: str, app_context: str = "") -> Optional[UIElement]:
        """
        Locate a UI element on screen by natural language description.
        
        Args:
            query: Description of element (e.g. "Play button")
            app_context: Optional context (e.g. "Apple Music")
            
        Returns:
            UIElement with absolute screen coordinates or None if not found.
        """
        # Capture screen
        base64_img = self.computer.get_screenshot_base64(resize_ratio=1.0) # Full resolution for precision
        screen_w, screen_h = self.computer.get_screen_size()
        
        prompt = f"""You are a GUI Automation Expert.
I have provided a screenshot of my macOS desktop.
Active App Context: {app_context}

TASK: Find the exact center coordinates of the UI element described as: "{query}"

INSTRUCTIONS:
1. Analyze the image to locate the element.
2. Return the Center X and Center Y coordinates relative to the original image dimensions ({screen_w}x{screen_h}).
3. Return JSON ONLY. No markdown.

FORMAT:
{{
  "found": true,
  "x": 123,
  "y": 456,
  "confidence": 0.9,
  "reasoning": "Located the play icon in the bottom center control bar."
}}

If the element is NOT visible, set "found": false.
"""
        
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}", "detail": "high"}}
                ]
            }
        ]
        
        try:
            # Re-init client to be safe
            self.router.reinitialize_client()
            
            response = self.router.chat(
                messages=messages,
                model="gpt-5.2",
                temperature=0.0,
                max_tokens=300,
            )
            
            content = response["content"]
            # Clean up potential markdown formatting
            if "```json" in content:
                content = content.replace("```json", "").replace("```", "")
            
            data = json.loads(content)
            
            if data.get("found"):
                return UIElement(
                    x=int(data["x"]),
                    y=int(data["y"]),
                    label=query,
                    confidence=data.get("confidence", 0.5)
                )
            
            return None
            
        except Exception as e:
            print(f"Screen Analysis Error: {e}")
            return None

    def analyze_screen_state(self, question: str) -> str:
        """
        Ask a general question about the screen state.
        e.g. "Is the music playing?" or "What website is open?"
        """
        base64_img = self.computer.get_screenshot_base64(resize_ratio=0.5) # Lower res ok for general context
        
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": f"Analyze this screenshot and answer: {question}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]
            }
        ]
        
        try:
            response = self.router.chat(messages=messages, model="gpt-4o")
            return response["content"]
        except Exception as e:
            return f"Error analyzing state: {e}"


# Global instance
_analyzer = None

def get_screen_analyzer() -> ScreenAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ScreenAnalyzer()
    return _analyzer

"""
ARKA GUI Agent v2
A proper agentic implementation using the OODA Loop (Observe, Orient, Decide, Act).
"""

import time
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from arka.agents.base_agent import BaseAgent, AgentResult
from arka.core.computer_controller import get_computer_controller
from arka.core.browser_manager import get_browser_manager
from arka.vision.screen_analyzer import get_screen_analyzer, UIElement
from arka.core.model_router import ModelRouter


@dataclass
class GuiAction:
    """Represents a single GUI action."""
    action_type: str  # "click", "type", "open_app", "wait", "done", "fail"
    target: str       # What to click or type
    reasoning: str    # Why this action


class GuiAgent(BaseAgent):
    """
    Agent for GUI automation using a proper OODA loop.
    """
    
    AGENT_TYPE = "gui"
    AGENT_ICON = "🖥️"
    MAX_STEPS = 15
    
    def __init__(self, router, tracker, tool_executor=None, model_override=None):
        super().__init__(router, tracker, model_override, tool_executor)
        self.computer = get_computer_controller()
        self.browser = get_browser_manager()
        self.analyzer = get_screen_analyzer()
        self.action_history: List[str] = []
        
    def process(self, task: str) -> AgentResult:
        """
        Execute a GUI task. Uses hybrid approach:
        - Specific browser mentioned (Comet, Safari, etc.) → Vision-based OODA loop
        - Generic web/YouTube (no browser specified) → Playwright + Vision
        - Desktop app tasks → Vision-based OODA loop
        """
        task_lower = task.lower()
        
        # Check if a SPECIFIC browser is mentioned - use vision for those
        specific_browsers = ['comet', 'safari', 'firefox', 'arc', 'brave', 'edge']
        uses_specific_browser = any(browser in task_lower for browser in specific_browsers)
        
        # Detect generic web tasks (no specific browser)
        web_keywords = ['youtube', 'website', 'http', 'www.', '.com', '.org', 'google']
        is_web_task = any(kw in task_lower for kw in web_keywords)
        
        # If specific browser mentioned, use vision-based OODA (controls their actual browser)
        # If generic web task, use Playwright (launches Chrome)
        if uses_specific_browser:
            # User wants to control a specific browser - use vision
            return self._execute_desktop_task(task)
        elif is_web_task:
            # Generic web task - use Playwright for reliability
            return self._execute_web_task(task)
        else:
            # Desktop app - use vision
            return self._execute_desktop_task(task)
    
    def _execute_web_task(self, task: str) -> AgentResult:
        """
        Hybrid approach: Playwright for navigation + Vision for finding results.
        - Playwright: reliable navigation, typing, page control
        - Vision: finding the right video/result to click
        """
        start_time = time.time()
        self.action_history = []
        
        try:
            task_lower = task.lower()
            
            # Start Playwright browser
            self.browser.start()
            self.action_history.append("Step 1: Started Playwright browser")
            
            if "youtube" in task_lower:
                return self._youtube_workflow(task, start_time)
            else:
                # Generic web navigation
                url = self._extract_url(task)
                if url:
                    self.browser.navigate(url)
                    self.action_history.append(f"Step 2: Navigated to {url}")
                    return AgentResult(
                        success=True,
                        output=f"✅ Opened {url}\n\nActions:\n" + "\n".join(self.action_history),
                        model="playwright+vision",
                        input_tokens=0,
                        output_tokens=0,
                        duration=time.time() - start_time,
                    )
            
            return AgentResult(
                success=False,
                output="❌ Could not determine what to do\n\nActions:\n" + "\n".join(self.action_history),
                model="playwright+vision",
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                output=f"❌ Error: {e}\n\nActions:\n" + "\n".join(self.action_history),
                model="playwright+vision",
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time,
            )
    
    def _youtube_workflow(self, task: str, start_time: float) -> AgentResult:
        """YouTube-specific workflow using Playwright + Vision."""
        try:
            # Step 1: Navigate to YouTube (Playwright - reliable)
            self.browser.navigate("https://www.youtube.com")
            self.action_history.append("Step 2: Navigated to YouTube")
            time.sleep(2)
            
            # Step 2: Extract and search (Playwright - reliable)
            search_query = self._extract_search_query(task)
            if not search_query:
                return AgentResult(
                    success=False,
                    output="❌ Could not extract search query from task",
                    model="playwright+vision",
                    input_tokens=0,
                    output_tokens=0,
                    duration=time.time() - start_time,
                )
            
            # Type in search box (Playwright)
            self.browser.page.click('input[name="search_query"]', timeout=5000)
            self.browser.page.fill('input[name="search_query"]', search_query)
            self.browser.page.keyboard.press('Enter')
            self.action_history.append(f"Step 3: Searched for '{search_query}'")
            time.sleep(3)  # Wait for results
            
            # Step 3: Find and click result using VISION
            # Take screenshot of the browser page
            screenshot_b64 = self.browser.screenshot()
            
            # Ask vision to find the best video result
            element = self._vision_find_video_result(screenshot_b64, search_query)
            
            if element:
                # Click using Playwright at the coordinates
                self.browser.page.mouse.click(element.x, element.y)
                self.action_history.append(f"Step 4: Vision found and clicked video at ({element.x}, {element.y})")
            else:
                # Fallback: try CSS selector
                try:
                    self.browser.page.click('ytd-video-renderer a#video-title', timeout=5000)
                    self.action_history.append("Step 4: Clicked first video (CSS fallback)")
                except:
                    self.action_history.append("Step 4: Could not find video to click")
                    return AgentResult(
                        success=False,
                        output=f"❌ Could not find video results\n\nActions:\n" + "\n".join(self.action_history),
                        model="playwright+vision",
                        input_tokens=0,
                        output_tokens=0,
                        duration=time.time() - start_time,
                    )
            
            time.sleep(2)
            self.action_history.append("Step 5: Video playing")
            
            return AgentResult(
                success=True,
                output=f"✅ Playing '{search_query}' on YouTube\n\nActions:\n" + "\n".join(self.action_history),
                model="playwright+vision",
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time,
            )
            
        except Exception as e:
            self.action_history.append(f"Error: {e}")
            return AgentResult(
                success=False,
                output=f"❌ YouTube workflow failed: {e}\n\nActions:\n" + "\n".join(self.action_history),
                model="playwright+vision",
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time,
            )
    
    def _vision_find_video_result(self, screenshot_b64: str, search_query: str):
        """Use vision to find the best video result to click."""
        prompt = f"""You are looking at YouTube search results for "{search_query}".
Find the FIRST video result thumbnail or title that matches the search query.

Return the coordinates to click in this EXACT format:
{{"found": true, "x": 123, "y": 456, "description": "first video result"}}

Or if no results visible:
{{"found": false}}

Remember: 
- Look for video thumbnails (rectangular images) 
- Video titles are blue/black text next to thumbnails
- Click in the CENTER of either the thumbnail or title
- Ignore ads (they say "Ad" next to them)"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}", "detail": "high"}}
                ]
            }
        ]
        
        try:
            response = self.router.chat(
                messages=messages,
                model="gpt-5.2",
                max_tokens=150,
            )
            
            content = response.get("content", "")
            import re
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("found"):
                    return UIElement(
                        x=int(data["x"]),
                        y=int(data["y"]),
                        label=data.get("description", "video"),
                        confidence=0.8
                    )
        except Exception as e:
            print(f"[Vision] Error finding video: {e}")
        
        return None
    
    def _extract_search_query(self, task: str) -> str:
        """Extract what to search for from the task."""
        import re
        # Look for patterns like "play X", "search for X", "find X"
        patterns = [
            r'play\s+(.+?)(?:\s+in|\s+on|\s+$)',
            r'search\s+(?:for\s+)?(.+?)(?:\s+in|\s+on|\s+$)',
            r'find\s+(.+?)(?:\s+in|\s+on|\s+$)',
            r'watch\s+(.+?)(?:\s+in|\s+on|\s+$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, task.lower())
            if match:
                return match.group(1).strip()
        return ""
    
    def _extract_url(self, task: str) -> str:
        """Extract URL from task."""
        import re
        # Look for domain names
        match = re.search(r'((?:https?://)?(?:www\.)?[\w.-]+\.(?:com|org|net|io|dev|ai))', task.lower())
        if match:
            url = match.group(1)
            if not url.startswith('http'):
                url = 'https://' + url
            return url
        return ""
        
    def _execute_desktop_task(self, task: str) -> AgentResult:
        """Execute a desktop app task using vision-based OODA loop."""
        start_time = time.time()
        self.action_history = []
        total_tokens = 0
        
        for step in range(self.MAX_STEPS):
            # === OBSERVE: Capture current screen state ===
            screenshot_b64 = self.computer.get_screenshot_base64(resize_ratio=0.75)
            active_app = self.computer.get_active_app()
            
            # === ORIENT + DECIDE: Ask LLM what to do next ===
            action = self._decide_next_action(task, screenshot_b64, active_app)
            total_tokens += action.get("tokens", 0)
            
            parsed_action = self._parse_action(action.get("content", ""))
            self.action_history.append(f"Step {step+1}: {parsed_action.action_type} -> {parsed_action.target}")
            
            # === ACT: Execute the action ===
            if parsed_action.action_type == "done":
                return AgentResult(
                    success=True,
                    output=f"✅ Task completed: {parsed_action.reasoning}\n\nActions taken:\n" + "\n".join(self.action_history),
                    model="gpt-4o",
                    input_tokens=total_tokens,
                    output_tokens=0,
                    duration=time.time() - start_time,
                )
            
            if parsed_action.action_type == "fail":
                return AgentResult(
                    success=False,
                    output=f"❌ Task failed: {parsed_action.reasoning}",
                    model="gpt-4o",
                    input_tokens=total_tokens,
                    output_tokens=0,
                    duration=time.time() - start_time,
                )
            
            result = self._execute_action(parsed_action)
            self.action_history[-1] += f" ({result})"
            
            # Small delay for UI to update
            time.sleep(0.5)
        
        return AgentResult(
            success=False,
            output=f"⚠️ Max steps ({self.MAX_STEPS}) reached. Actions taken:\n" + "\n".join(self.action_history),
            model="gpt-4o",
            input_tokens=total_tokens,
            output_tokens=0,
            duration=time.time() - start_time,
        )
    
    def _decide_next_action(self, task: str, screenshot_b64: str, active_app: str) -> Dict:
        """Ask LLM to decide the next action based on screen state."""
        history_str = "\n".join(self.action_history[-5:]) if self.action_history else "None yet."
        
        # Detect if stuck in a loop
        loop_warning = ""
        if len(self.action_history) >= 3:
            recent = [h.split(" -> ")[1].split(" (")[0] if " -> " in h else "" for h in self.action_history[-3:]]
            if len(set(recent)) == 1:
                loop_warning = "\n⚠️ WARNING: You're repeating the same action. Try something DIFFERENT!"
        
        prompt = f"""You are a macOS GUI automation agent. Task: "{task}"

STATE:
- Active app: {active_app}
- History: {history_str}{loop_warning}

AVAILABLE ACTIONS:

1. open_app - Open/focus an app
   {{"action": "open_app", "target": "Comet", "reasoning": "..."}}

2. hotkey - Press keyboard shortcut (PREFERRED for browser!)
   {{"action": "hotkey", "target": "cmd+t", "reasoning": "New tab"}}
   {{"action": "hotkey", "target": "cmd+l", "reasoning": "Focus address bar"}}
   {{"action": "hotkey", "target": "cmd+a", "reasoning": "Select all text"}}

3. click - Click on a visible element
   {{"action": "click", "target": "play button", "reasoning": "..."}}

4. type - Type text (only after focusing a text field!)
   {{"action": "type", "target": "youtube.com", "reasoning": "..."}}

5. press_key - Single key press
   {{"action": "press_key", "target": "enter", "reasoning": "Submit"}}

6. wait - Wait for page load (1.5s)
7. done - Task complete
8. fail - Cannot complete

BROWSER WORKFLOW (USE HOTKEYS!):
1. open_app "Comet"
2. hotkey "cmd+t" (new tab - MORE RELIABLE than clicking!)
3. hotkey "cmd+l" (focus address bar - MORE RELIABLE!)
4. type "youtube.com"
5. press_key "enter"
6. wait
7. click "Search" box on YouTube
8. type "bolo bolo"
9. press_key "enter"
10. wait
11. click on video thumbnail
12. done

RULES:
- USE hotkey for browser navigation - it's more reliable than clicking!
- If an action fails, try a DIFFERENT approach
- Look at the ACTUAL screenshot, not what you expect

JSON ONLY:
{{"action": "...", "target": "...", "reasoning": "..."}}"""
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot_b64}", "detail": "high"}}
                ]
            }
        ]
        
        try:
            response = self.router.chat(
                messages=messages,
                model="gpt-5.2",
                temperature=0.0,
                max_tokens=300,
            )
            return {
                "content": response.get("content", ""),
                "tokens": response.get("input_tokens", 0) + response.get("output_tokens", 0)
            }
        except Exception as e:
            return {"content": f'{{"action": "fail", "target": "", "reasoning": "Error: {e}"}}', "tokens": 0}
    
    def _parse_action(self, content: str) -> GuiAction:
        """Parse LLM response into a GuiAction with robust error handling."""
        import re
        
        original_content = content  # Keep for debugging
        
        try:
            # Clean up markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
            
            # Try to extract JSON object from the content
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                content = json_match.group()
            
            # Fix common JSON issues
            content = content.strip()
            content = content.replace("'", '"')  # Single to double quotes
            content = re.sub(r',\s*}', '}', content)  # Trailing commas
            content = re.sub(r',\s*]', ']', content)  # Trailing commas in arrays
            # Fix unescaped quotes in values
            content = re.sub(r'(?<!\\)"(?=[^:,}\]]*[,}\]])', '\\"', content)
            
            data = json.loads(content)
            return GuiAction(
                action_type=data.get("action", "fail"),
                target=data.get("target", ""),
                reasoning=data.get("reasoning", "")
            )
        except Exception as e:
            pass  # Fall through to regex fallback
        
        # Fallback: try to extract action using regex from original content
        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', original_content)
        target_match = re.search(r'"target"\s*:\s*"([^"]*)"', original_content)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', original_content)
        
        if action_match:
            return GuiAction(
                action_type=action_match.group(1),
                target=target_match.group(1) if target_match else "",
                reasoning=reasoning_match.group(1) if reasoning_match else "Regex fallback"
            )
        
        # Last resort: look for action keywords anywhere
        content_lower = original_content.lower()
        if "open_app" in content_lower or "open app" in content_lower:
            app_match = re.search(r'(?:apple music|safari|chrome|comet|finder)', content_lower)
            return GuiAction(
                action_type="open_app",
                target=app_match.group(0).title() if app_match else "Apple Music",
                reasoning="Extracted from natural language"
            )
        
        print(f"[DEBUG] Failed to parse: {original_content[:200]}")
        return GuiAction(action_type="wait", target="", reasoning="Parse failed, waiting")
    
    def _execute_action(self, action: GuiAction) -> str:
        """Execute a single GUI action."""
        try:
            if action.action_type == "click":
                # Use vision to find and click
                element = self.analyzer.find_element(action.target)
                if element:
                    self.computer.click(element.x, element.y)
                    return f"Clicked at ({element.x}, {element.y})"
                else:
                    return f"Could not find '{action.target}'"
            
            elif action.action_type == "type":
                # Clean the text - remove any escape sequences
                text = action.target.replace("\\n", "").replace("\n", "").strip()
                if text:
                    self.computer.type_text(text)
                    return f"Typed '{text}'"
                else:
                    return "Nothing to type (empty text)"
            
            elif action.action_type == "hotkey":
                # Parse hotkey like "cmd+t" or "cmd+shift+n"
                parts = action.target.lower().replace("command", "cmd").replace("ctrl", "ctrl").split("+")
                # Map modifier names
                modifier_map = {"cmd": "command", "ctrl": "ctrl", "alt": "option", "shift": "shift"}
                modifiers = []
                key = None
                for part in parts:
                    part = part.strip()
                    if part in modifier_map:
                        modifiers.append(modifier_map[part])
                    else:
                        key = part
                if key:
                    self.computer.press_key(key, modifiers if modifiers else None)
                    return f"Pressed {'+'.join(modifiers + [key])}"
                return "Invalid hotkey format"
            
            elif action.action_type == "press_key":
                # Map common key names to pyautogui names
                key_map = {
                    "enter": "return",
                    "return": "return", 
                    "escape": "escape",
                    "esc": "escape",
                    "tab": "tab",
                    "backspace": "backspace",
                    "delete": "delete",
                    "space": "space",
                    "up": "up",
                    "down": "down",
                    "left": "left",
                    "right": "right",
                }
                key = action.target.lower().strip()
                key = key_map.get(key, key)
                self.computer.press_key(key)
                return f"Pressed '{key}'"
            
            elif action.action_type == "open_app":
                success = self.computer.open_app(action.target)
                if success:
                    return f"Opened {action.target}"
                else:
                    return f"Failed to open {action.target} - app not found"
            
            elif action.action_type == "wait":
                time.sleep(1.5)
                return "Waited 1.5s"
            
            else:
                return f"Unknown action: {action.action_type}"
                
        except Exception as e:
            return f"Error: {e}"

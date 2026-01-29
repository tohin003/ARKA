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
from arka.memory.memory_client import MemoryClient
from arka.training.rl_trainer import get_trainer
from arka.config import get_config
from arka.agents.form_pipeline import FormFillingPipeline


@dataclass
class GuiAction:
    """Represents a single GUI action."""
    action_type: str  # "click", "type", "open_app", "wait", "done", "fail"
    target: str       # What to click or type
    reasoning: str    # Why this action
    text: str = ""    # For dom_type (separate from target ID)


class GuiAgent(BaseAgent):
    """
    Agent for GUI automation using a proper OODA loop with self-reflection.
    
    Features:
    - Checkpoint-based execution (every 5 steps)
    - Adaptive o1 usage (learned tasks use gpt-5.2, new tasks use o1)
    - Step-level feedback learning
    """
    
    AGENT_TYPE = "gui"
    AGENT_ICON = "🖥️"
    MAX_STEPS = 50
    CHECKPOINT_INTERVAL = 5       # Reflect every 5 steps
    MAX_CHECKPOINTS = 10          # Max reflections per task
    CONFIDENCE_THRESHOLD = 0.8    # Skip o1 if confidence > this
    
    def __init__(self, router, tracker, tool_executor=None, model_override=None):
        super().__init__(router, tracker, model_override, tool_executor)
        self.computer = get_computer_controller()
        self.browser = get_browser_manager()
        self.analyzer = get_screen_analyzer()
        self.memory = MemoryClient()
        self.trainer = get_trainer()
        self.config = get_config()
        
        # Stop/Pause Flag
        self.stop_flag = False
        
        # Action tracking
        self.action_history: List[str] = []
        
        # Checkpoint state
        self.step_history: List[Dict] = []      # Detailed step info
        self.current_plan: List[str] = []        # o1's planned steps
        self.current_task: str = ""              # Current task for feedback
        
        # Form pipeline (lazy init)
        self._form_pipeline: Optional[FormFillingPipeline] = None
        
    def process(self, task: str) -> AgentResult:
        """
        Execute a GUI task. Uses hybrid approach:
        - Form filling tasks → FormFillingPipeline (gpt-5.2 + o1)
        - Specific browser mentioned (Comet, Safari, etc.) → Vision-based OODA loop
        - Generic web/YouTube (no browser specified) → Playwright + Vision
        - Desktop app tasks → Vision-based OODA loop
        """
        task_lower = task.lower()
        
        # Check for form-filling tasks → use dedicated pipeline
        form_keywords = ['fill form', 'fill the form', 'fill out', 'apply', 'application', 'submit form']
        if any(kw in task_lower for kw in form_keywords):
            return self._execute_form_filling(task)
        
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
    
    def _execute_form_filling(self, task: str) -> AgentResult:
        """
        Execute form filling using the dedicated pipeline.
        Uses gpt-5.2 for vision and o1 for reasoning.
        """
        start_time = time.time()
        
        print("\n" + "="*60)
        print("📝 FORM FILLING PIPELINE ACTIVATED")
        print("   Vision Model: gpt-5.2 | Reasoning Model: o1")
        print("="*60)
        
        # Lazy initialize pipeline
        if self._form_pipeline is None:
            self._form_pipeline = FormFillingPipeline(self.router, self.memory)
        
        # Ensure browser is connected
        if not self.browser.connect_external(9222):
            return AgentResult(
                success=False,
                output="❌ Failed to connect to browser. Ensure Comet is running with --remote-debugging-port=9222",
                model=self.config.models.gui_vision,
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time
            )
        
        # Run the pipeline
        result = self._form_pipeline.fill_form(task_context=task)
        
        # Format output
        if result["status"] in ["ready_to_submit", "corrected"]:
            filled_count = len(result["filled_fields"])
            output = f"✅ Form filled successfully!\n\n"
            output += f"📋 Filled {filled_count} fields:\n"
            for field in result["filled_fields"]:
                output += f"   • {field['question'][:40]}... → {field['answer']} ({field['source']})\n"
            
            if result.get("review_result"):
                review = result["review_result"]
                if review.approved:
                    output += "\n✅ Final review: APPROVED"
                else:
                    output += f"\n⚠️ Final review: {len(review.changes)} corrections applied"
            
            return AgentResult(
                success=True,
                output=output,
                model=self.config.models.gui_vision,
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time
            )
        else:
            errors = "\n".join(result.get("errors", []))
            return AgentResult(
                success=False,
                output=f"❌ Form filling failed:\n{errors}",
                model=self.config.models.gui_vision,
                input_tokens=0,
                output_tokens=0,
                duration=time.time() - start_time
            )
    
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
        """Execute a desktop app task using vision-based OODA loop with checkpoints."""
        start_time = time.time()
        self.action_history = []
        self.step_history = []
        self.current_plan = []
        self.current_task = task
        total_tokens = 0
        steps_since_checkpoint = 0
        
        # Initial checking for similar tasks to set confidence
        confidence, patterns = self._check_task_experience(task)
        if confidence > self.CONFIDENCE_THRESHOLD:
            print(f"🧠 High confidence ({confidence:.2f}) from past tasks. Using self-evaluation.")
        
        for step in range(self.MAX_STEPS):
            # === PAUSE CHECK ===
            if self.stop_flag:
                print(f"\n[PAUSED] Task interrupted by user.")
                self.computer.send_notification("Task Paused", "Agent stopped by shortcut (Cmd+Shift+P).")
                
                # Format taken steps
                steps_str = "\n".join([f"{i+1}. {act}" for i, act in enumerate(self.action_history)])
                
                return AgentResult(
                    success=False,
                    output=f"Task stopped by user.\n\nSteps taken before pause:\n{steps_str}",
                    model=self.config.models.gui_vision,
                    duration=time.time() - start_time,
                    error="Interrupted by User"
                )

            # === CHECKPOINT REFLECTION ===
            if step > 0 and steps_since_checkpoint >= self.CHECKPOINT_INTERVAL:
                checkpoints_count = getattr(self, 'checkpoints_count', 0) + 1
                self.checkpoints_count = checkpoints_count
                
                if checkpoints_count > self.MAX_CHECKPOINTS:
                     print("❌ Checkpoint Limit Reached")
                     return AgentResult(success=False, output="❌ Terminated: Too many planning loops without success.")

                print(f"🛑 Checkpoint {checkpoints_count} (Step {step}). Reflecting...")
                
                active_app = self.computer.get_active_app()
                is_browser = any(b in active_app for b in ["Chrome", "Comet", "Safari", "Arc", "Brave", "Edge"])
                
                # Reflect and update plan
                # Pass recent history to detect loops explicitly
                reflection = self._checkpoint_reflect(task, is_browser, confidence, patterns, self.action_history[-5:])
                
                if reflection.get("success_detected"):
                    print(f"✅ Success detected during reflection! Marking task as done.")
                    return AgentResult(
                        success=True,
                        output=f"✅ Task completed (verified by checkpoint): {reflection.get('feedback')}\n\nActions:\n" + "\n".join(self.action_history),
                        model=self.config.models.gui_vision,
                        duration=time.time() - start_time
                    )

                if not reflection.get("on_track", True):
                    print(f"⚠️ Course correction needed: {reflection.get('feedback')}")
                
                if reflection.get("plan"):
                    self.current_plan = reflection["plan"]
                    print(f"📋 New Plan: {self.current_plan}")
                
                steps_since_checkpoint = 0

            # === OBSERVE: Capture current screen state ===
            screenshot_b64 = self.computer.get_screenshot_base64(resize_ratio=0.75)
            active_app = self.computer.get_active_app()
            
            # === HYBRID CONTEXT: Get DOM if browser ===
            dom_snippet = ""
            is_browser = any(b in active_app for b in ["Chrome", "Comet", "Safari", "Arc", "Brave", "Edge"])
            if is_browser:
                # Ensure we're connected to the browser via CDP
                if not getattr(self, '_browser_connected', False):
                    self._browser_connected = self.browser.connect_external(9222)
                    
                if self._browser_connected:
                    # Try to get DOM snapshot
                    snap = self.browser.get_dom_snapshot()
                    if snap and "Error" not in snap:
                        # Limit to first 50 elements to avoid token overflow
                        lines = snap.split('\n')[:50]
                        dom_snippet = '\n'.join(lines)

            # === MEMORY CONTEXT: Check for form/application tasks ===
            memory_context = ""
            task_lower = task.lower()
            # Expanded keywords for form filling scenarios
            memory_triggers = ["tohin", "user", "fill", "form", "apply", "application", "job", "linkedin", "indeed", "resume", "salary", "interview"]
            if any(trigger in task_lower for trigger in memory_triggers):
                try:
                    # Search for user info in the tohin_the_user node
                    results = self.memory.search(
                        "user personal information salary job experience",
                        limit=10,
                        filter_metadata={"node": "tohin_the_user"}
                    )
                    if results:
                        user_data = "\n".join([r.content[:200] for r in results])
                        memory_context = f"USER INFO (for forms):\n{user_data}"
                except Exception as e:
                    print(f"[DEBUG] Memory load failed: {e}")

            # === ORIENT + DECIDE: Ask LLM what to do next ===
            action = self._decide_next_action(task, screenshot_b64, active_app, dom_snippet, memory_context)
            total_tokens += action.get("tokens", 0)
            
            parsed_action = self._parse_action(action.get("content", ""))
            self.action_history.append(f"Step {step+1}: {parsed_action.action_type} -> {parsed_action.target}")
            
            # === STORE STEP ===
            self._store_step(step+1, parsed_action, dom_snippet, screenshot_b64)
            
            # === ACT: Execute the action ===
            if parsed_action.action_type == "done":
                # Save success feedback automatically
                if self.trainer:
                    self.trainer.log_interaction(
                        task=task,
                        response=parsed_action.reasoning,
                        success=True,
                        user_feedback="implicit_success",
                        metadata={"agent": "gui", "steps": len(self.action_history)}
                    )
                self.computer.send_notification("Task Complete", f"Successfully completed: {task}")
                return AgentResult(
                    success=True,
                    output=f"✅ Task completed: {parsed_action.reasoning}\n\nActions taken:\n" + "\n".join(self.action_history),
                    model=self.config.models.gui_vision,
                    input_tokens=total_tokens,
                    output_tokens=0,
                    duration=time.time() - start_time,
                )
            
            if parsed_action.action_type == "fail":
                return AgentResult(
                    success=False,
                    output=f"❌ Task failed: {parsed_action.reasoning}",
                    model=self.config.models.gui_vision,
                    input_tokens=total_tokens,
                    output_tokens=0,
                    duration=time.time() - start_time,
                )
            
            result = self._execute_action(parsed_action)
            self.action_history[-1] += f" ({result})"
            
            steps_since_checkpoint += 1
            
            # Small delay for UI to update (CRITICAL: Wait long enough for animations/network)
            time.sleep(2.5)
        
        return AgentResult(
            success=False,
            output=f"⚠️ Max steps ({self.MAX_STEPS}) reached. Actions taken:\n" + "\n".join(self.action_history),
            model=self.config.models.gui_vision,
            input_tokens=total_tokens,
            output_tokens=0,
            duration=time.time() - start_time,
        )

    def _store_step(self, step_num: int, action: GuiAction, dom: str, screenshot_b64: str):
        """Store step details for reflection."""
        # Clean dom to save space
        dom_preview = dom[:1000] if dom else ""
        
        self.step_history.append({
            "step": step_num,
            "action": action.action_type,
            "target": action.target,
            "reasoning": action.reasoning,
            "dom_context": dom_preview,
            "timestamp": time.time()
        })
        # Keep history manageable
        if len(self.step_history) > 20:
            self.step_history.pop(0)

    def _check_task_experience(self, task: str) -> tuple:
        """Check if we have successfully done this task before."""
        try:
            results = self.memory.search(
                task, 
                limit=1, 
                filter_metadata={"node": "gui_learning", "success": True}
            )
            if results:
                score = getattr(results[0], 'score', 0.0)
                return score, results[0].content
        except Exception:
            pass
        return 0.0, None

    def _checkpoint_reflect(self, task: str, is_web: bool, confidence: float, patterns: str, recent_actions: List[str] = []) -> Dict:
        """Reflect on progress using either self-evaluation (learned) or o1 (new)."""
        if confidence > self.CONFIDENCE_THRESHOLD:
             print(f"🧠 Using fast self-evaluation (Confidence: {confidence:.2f})")
             return self._self_evaluate(task, patterns)
        
        print(f"🤔 Using deep reasoning (o1) for evaluation...")
        try:
            evaluation = self._o1_evaluate(task, is_web, patterns, timeout=60)
            
            # Check for success
            if evaluation.get("success_detected", False):
                return evaluation

            # User Architecture Requirement: Always get next 5 steps from o1 if not done
            print(f"🔄 Checkpoint: Getting next 5 steps from o1...")
            plan_res = self._o1_plan(task, evaluation, patterns, recent_actions, timeout=60)
            evaluation["plan"] = plan_res.get("plan", [])
            
            # Store for learning if correction needed
            if not evaluation.get("on_track", True) and self.trainer:
                self.trainer.save_checkpoint_feedback(task, self.step_history[-5:], evaluation)
                
            return evaluation
        except Exception as e:
            print(f"⚠️ Reflection failed: {e}")
            return {"on_track": True, "plan": []}

    def _self_evaluate(self, task: str, patterns: str) -> Dict:
        """Fast self-evaluation using gpt-5.2 and learned patterns."""
        # Future: ask gpt-5.2 if we match patterns
        return {"on_track": True, "plan": []}

    def _o1_evaluate(self, task: str, is_web: bool, patterns: str = None, timeout: int = 60) -> Dict:
        """Ask o1 if we are on track."""
        recent_steps = self.step_history[-5:]
        context_str = ""
        
        # Inject learned patterns/mistakes
        rl_context = ""
        if patterns:
             # If patterns is a string, use it. If it's structured, format it.
             rl_context = f"\n\n=== REINFORCEMENT LEARNING CONTEXT ===\n{patterns}\n======================================"

        messages = []
        
        prompt_instruction = (
            f"TASK: {task}\nSTEPS TAKEN:\n{recent_steps}{rl_context}\n\n"
            "Assess progress strictly. Return JSON { 'on_track': bool, 'feedback': str, 'success_detected': bool }.\n"
            "CRITICAL:\n"
            "- If the task goal appears achieved (e.g. video is playing, page is loaded, form is submitted), "
            "set 'success_detected': true and 'on_track': true.\n"
            "- Do NOT propose new plans if the goal is met. Return success."
        )

        if is_web:
             # Use last DOM context
             last_dom = recent_steps[-1].get("dom_context", "") if recent_steps else ""
             context_str = f"Context (DOM):\n{last_dom}"
             messages = [{"role": "user", "content": prompt_instruction + f"\n{context_str}"}]
        else:
             # Desktop: use screenshot
             screenshot_b64 = self.computer.get_screenshot_base64(resize_ratio=0.5)
             messages = [{
                 "role": "user", 
                 "content": [
                    {"type": "text", "text": prompt_instruction + "\nLook at the screenshot to confirm success (e.g., video playing)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                 ]
             }]

        response = self.router.chat(
            messages=messages,
            model=self.config.models.gui_reasoner, # o1
        )
        try:
            content = response.get("content", "{}").strip()
            # Basic cleanup if markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except:
            return {"on_track": True, "feedback": "Parse error"}

    def _o1_plan(self, task: str, evaluation: Dict, patterns: str = None, recent_actions: List[str] = [], timeout: int = 60) -> Dict:
        """Ask o1 for a recovery plan."""
        # Inject learned patterns explicitly for planning
        rl_context = ""
        if patterns:
             rl_context = f"\n\n=== LEARNED PATTERNS (DO NOT IGNORE) ===\n{patterns}\n========================================"

        history_str = "\n".join(recent_actions) if recent_actions else "None"
        
        messages = [{"role": "user", "content": f"TASK: {task}\nFEEDBACK: {evaluation.get('feedback')}{rl_context}\nRECENT ACTIONS: {history_str}\n\n"
                                                f"Provide the NEXT 5 steps to move forward. Return JSON {{'plan': [step1, step2]}}.\n"
                                                f"IMPORTANT: Do NOT repeat actions that just happened. Focus on progress."}]
        response = self.router.chat(
            messages=messages,
            model=self.config.models.gui_reasoner,
        )
        try:
            content = response.get("content", "{}").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content)
        except:
            return {"plan": []}

    def _decide_next_action(self, task: str, screenshot_b64: str, active_app: str, dom_snippet: str = "", memory_context: str = "") -> Dict:
        """Ask LLM to decide the next action based on screen state and DOM."""
        history_str = "\n".join(self.action_history[-5:]) if self.action_history else "None yet."
        
        # Detect if stuck in a loop
        loop_warning = ""
        if len(self.action_history) >= 3:
            recent = [h.split(" -> ")[1].split(" (")[0] if " -> " in h else "" for h in self.action_history[-3:]]
            if len(set(recent)) == 1:
                loop_warning = "\n⚠️ WARNING: You're repeating the same action. Try something DIFFERENT!"
        
        # Fetch learned mistakes for this task
        mistakes = self.trainer.get_mistakes(task) if self.trainer else []
        mistakes_str = ""
        if mistakes:
            mistakes_str = "\n⚠️ LEARNED MISTAKES & CORRECTIONS (PAY ATTENTION):"
            for m in mistakes:
                # Differentiate between generic mistakes and specific corrections
                act = m['action'][:100].replace("\n", " ")
                feedback = m.get('feedback', 'Failed')
                
                if "CORRECTION:" in feedback:
                    # Step Correction - Stronger instruction
                    mistakes_str += f"\n- 🛑 STOP! If you were about to: {act}"
                    mistakes_str += f"\n  ✅ DO THIS INSTEAD: {feedback.replace('CORRECTION:', '').strip()}"
                else:
                    # General mistake
                    mistakes_str += f"\n- AVOID: {act} (Why: {feedback})"
        
        # Inject Current Plan
        plan_str = ""
        if self.current_plan:
             plan_str = f"\n\n=== CURRENT PLAN FROM REASONER (STRICTLY FOLLOW) ===\n" + "\n".join([f"- {s}" for s in self.current_plan]) + "\n===================================================="

        prompt = f"""You are a macOS GUI automation agent. Task: "{task}"{plan_str}

THINK STEP BY STEP:
1. What is the goal? → {task}
2. CHECK PLAN: What is the next uncompleted step in the CURRENT PLAN above?
3. What do I see on screen? (Screenshot)
4. What DOM elements are available? (DOM List)
5. What is the SINGLE best action to execute the current plan step?

STATE:
- Active app: {active_app}
- History: {history_str}{loop_warning}{mistakes_str}

DOM CONTEXT (Interactive Web Elements):
{dom_snippet if dom_snippet else "No DOM data available."}

MEMORY CONTEXT (User Info):
{memory_context if memory_context else "No specific memory loaded."}
        
AVAILABLE ACTIONS:

1. dom_click - CLICK BY ID (PREFERRED for Web)
   {{"action": "dom_click", "target": "12", "reasoning": "Clicking 'Submit' button by ID"}}
   * Use the numeric ID [x] from the DOM list above.

2. dom_type - TYPE INTO ID (PREFERRED for Web)
   {{"action": "dom_type", "target": "12", "text": "hello", "reasoning": "Typing into search field ID 12"}}

3. dom_select - SELECT DROPDOWN OPTION (for <select> elements)
   {{"action": "dom_select", "target": "4", "text": "No", "reasoning": "Selecting 'No' in passport dropdown"}}
   * Use this for dropdown/select elements to pick an option by its visible text.

3. open_app - Open/focus an app
   {{"action": "open_app", "target": "Comet", "reasoning": "..."}}

4. hotkey - Press keyboard shortcut
   {{"action": "hotkey", "target": "cmd+t", "reasoning": "New tab"}}
   
5. hover - Hover over element (Reveal hidden UI)
   {{"action": "hover", "target": "song row", "reasoning": "Hovering to see play button"}}

6. click - Visual Click (Fallback for non-web)
   {{"action": "click", "target": "play button", "reasoning": "..."}}

7. type - Global Keyboard Type (Fallback)
   {{"action": "type", "target": "text", "reasoning": "..."}}

8. press_key - Single key press
   {{"action": "press_key", "target": "enter", "reasoning": "..."}}

9. wait - Wait for page load
10. done - Task complete
11. fail - Cannot complete

RULES:
- **WEB TASKS**: ALWAYS check the DOM List first! If you see the element there, use `dom_click` with its `[ID]`. It is 100% accurate.
- If DOM is empty/missing, fall back to `click` (Visual) or `hotkey`.
- `dom_type` requires an ID and text. Example: {{"action": "dom_type", "target": "5", "text": "800000"}}
- Use `cmd+l` to focus URL bar if you need to navigate.

**FORM FILLING WORKFLOW** (FOLLOW THIS EXACTLY!):
When you see a form with input fields:
1. Look at the DOM list for `<input>` or `<select>` elements with their [ID]
2. Match the label/placeholder to the question being asked
3. Get the answer from MEMORY CONTEXT if available, or infer from task
4. Use `dom_type` to fill EACH field: {{"action": "dom_type", "target": "ID", "text": "answer"}}
5. For dropdown/select: use `dom_click` on the ID, then `dom_click` on the option
6. After ALL fields are filled, click the Next/Submit button with `dom_click`

CRITICAL: You MUST actually FILL the form, not just describe what to fill!
- If you see an input field for "Expected Salary" and Memory says "800000", execute: {{"action": "dom_type", "target": "X", "text": "800000"}}
- Do NOT just tell the user what to fill. YOU fill it!

JSON ONLY:
{{"action": "...", "target": "...", "text": "...", "reasoning": "..."}}"""
        
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
                model=self.config.models.gui_vision,
                temperature=0.1,
                max_tokens=500,
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
                reasoning=data.get("reasoning", ""),
                text=data.get("text", "") # Added for dom_type
            )
        except Exception as e:
            pass  # Fall through to regex fallback
        
        # Fallback: try to extract action using regex from original content
        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', original_content)
        target_match = re.search(r'"target"\s*:\s*"([^"]*)"', original_content)
        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', original_content)
        text_match = re.search(r'"text"\s*:\s*"([^"]*)"', original_content)
        
        if action_match:
            return GuiAction(
                action_type=action_match.group(1),
                target=target_match.group(1) if target_match else "",
                reasoning=reasoning_match.group(1) if reasoning_match else "Regex fallback",
                text=text_match.group(1) if text_match else ""
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
            if action.action_type == "dom_click":
                # Use BrowserManager to click by ID
                try:
                    self.browser.click(action.target) # target is "12"
                    return f"DOM Clicked ID [{action.target}]"
                except Exception as e:
                    return f"DOM Click Failed: {e}"

            elif action.action_type == "dom_type":
                try:
                    self.browser.type_text(action.target, action.text)
                    return f"DOM Typed '{action.text}' into ID [{action.target}]"
                except Exception as e:
                    return f"DOM Type Failed: {e}"

            elif action.action_type == "dom_select":
                try:
                    result = self.browser.select_option(action.target, action.text)
                    return f"DOM Selected '{action.text}' in dropdown ID [{action.target}] - {result}"
                except Exception as e:
                    return f"DOM Select Failed: {e}"

            elif action.action_type == "hover":
                # Use vision to find and hover
                element = self.analyzer.find_element(action.target)
                if element:
                    self.computer.mouse_move(element.x, element.y)
                    return f"Hovered at ({element.x}, {element.y})"
                else:
                    return f"Could not find '{action.target}' to hover"

            elif action.action_type == "click":
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

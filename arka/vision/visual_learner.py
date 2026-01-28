"""
ARKA Visual Learner v2
Enhanced with continuous capture and RL integration.
"""

import time
import threading
from typing import Optional, List, Dict
from pathlib import Path

from arka.vision.screen_watcher import get_screen_watcher
from arka.core.model_router import ModelRouter
from arka.skills.skill_forge import get_skill_forge
from arka.training.rl_trainer import get_trainer
from arka.config import get_config


class VisualLearner:
    """
    Learns new skills by watching user actions on screen.
    Uses continuous capture and RL for improvement.
    """
    
    def __init__(self):
        self.watcher = get_screen_watcher()
        self.router = ModelRouter()
        self.forge = get_skill_forge()
        self.trainer = get_trainer()
        self.config = get_config()
        
        self.recording = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.task_name = ""
    
    def start_learning(self, task_name: str, interval: float = 0.5):
        """Start recording screen for learning a task (faster capture)."""
        if self.recording:
            return "Already recording."
        
        self.task_name = task_name
        self.watcher.start_session(f"learn_{task_name}_{int(time.time())}")
        self.recording = True
        self._stop_event.clear()
        
        # Start background capture thread with faster interval
        self._thread = threading.Thread(
            target=self._capture_loop,
            args=(interval,),
            daemon=True
        )
        self._thread.start()
        return f"Recording started for: {task_name}. Capturing every {interval}s. Type '/done' when finished."
    
    def _capture_loop(self, interval: float):
        """Background loop to capture frames continuously."""
        while not self._stop_event.is_set():
            self.watcher.capture_frame()
            time.sleep(interval)
    
    def stop_and_process(self, user_description: str = "") -> Dict:
        """Stop recording and process the captured frames to create a skill."""
        if not self.recording:
            return {"success": False, "message": "Not recording."}
        
        self.recording = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        
        frames = self.watcher.get_frames()
        if not frames:
            return {"success": False, "message": "No frames captured."}
        
        # Select more key frames for better analysis (up to 8)
        key_frames = self._select_key_frames(frames, max_frames=8)
        
        result = self._analyze_and_create_skill(key_frames, self.task_name, user_description)
        
        # Log to RL trainer
        self.trainer.log_interaction(
            task=f"Visual learning: {self.task_name}",
            response=result.get("steps_text", ""),
            success=result.get("success", False),
            metadata={"frames_captured": len(frames), "frames_analyzed": len(key_frames)}
        )
        
        return result
    
    def _select_key_frames(self, frames: List[Dict], max_frames: int = 8) -> List[Dict]:
        """Select key frames distributed across the recording."""
        total = len(frames)
        if total <= max_frames:
            return frames
        
        # Distribute evenly
        step = total / max_frames
        indices = [int(i * step) for i in range(max_frames)]
        return [frames[i] for i in indices]
    
    def _analyze_and_create_skill(self, frames: List[Dict], name: str, description: str) -> Dict:
        """Send frames to Vision model to reverse engineer the action."""
        
        # Build detailed prompt for better results
        content = [
            {
                "type": "text",
                "text": f"""You are an expert macOS automation engineer analyzing a screen recording.

TASK: "{name}"
DESCRIPTION: {description or "User demonstration"}

I'm showing you {len(frames)} screenshots in chronological order from a user performing this task.

IMPORTANT INSTRUCTIONS:
1. IGNORE any Terminal/command line windows - focus ONLY on the actual application being used (like Apple Music, Safari, Finder, etc.)
2. List EVERY action from START to FINISH including the FINAL action (like clicking play, selecting a result)
3. Be specific about button names, UI element positions, and exact text typed
4. The LAST frames are MOST IMPORTANT - they show task completion

REQUIRED OUTPUT FORMAT:

ANALYSIS:
Frame 1: [what you see]
Frame 2: [what you see]
...
Final Frame: [the completed action]

COMPLETE STEPS (from start to finish):
1. [First action]
2. [Second action]
...
N. [FINAL action like "Click Play button" or "Select first result"]

APPLESCRIPT CODE:
```applescript
-- Complete automation script
tell application "..."
    ...
end tell
```

Be VERY specific about the final play/select/click action. Do NOT skip any steps."""
            }
        ]
        
        for i, frame in enumerate(frames):
            base64_image = self.watcher.encode_image(frame["path"])
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high"
                }
            })
            
        messages = [{"role": "user", "content": content}]
        
        # Use gpt-4o for vision
        try:
            # Reinitialize to ensure API key is loaded
            self.router.reinitialize_client()
            
            response = self.router.chat(
                messages=messages,
                model="gpt-4o",
                max_tokens=2000,
                temperature=0.3  # Lower for more precise output
            ) 
            
            response_text = response["content"]
            
            # Extract steps from response - try multiple methods
            steps = self._extract_steps(response_text)
            
            # Even if step extraction failed, save the raw response as the skill
            if not steps or len(steps) < 2:
                # Fallback: use frame analysis as steps
                steps = self._extract_frame_analysis(response_text)
            
            if not steps:
                # Last resort: save raw response lines as steps
                steps = [line.strip() for line in response_text.split('\n') if line.strip() and len(line.strip()) > 10][:10]
            
            # Save to Skill Forge regardless
            self.forge.learn(
                name=name,
                description=description or f"Visually learned: {name}",
                steps=steps,
                metadata={
                    "source": "visual_learning_v2",
                    "frames": len(frames),
                    "raw_response": response_text[:2000]
                }
            )
            
            return {
                "success": True,
                "message": f"✓ Learned skill '{name}'",
                "steps": steps,
                "steps_text": response_text
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Vision analysis failed: {str(e)}",
                "steps_text": ""
            }
    
    def _extract_steps(self, text: str) -> List[str]:
        """Extract numbered steps from GPT response."""
        steps = []
        lines = text.split("\n")
        
        in_steps = False
        for line in lines:
            line = line.strip()
            # Multiple trigger phrases
            if any(kw in line.upper() for kw in ["STEPS:", "COMPLETE STEPS", "STEPS (", "ACTIONS:"]):
                in_steps = True
                continue
            if any(kw in line.upper() for kw in ["CODE:", "APPLESCRIPT", "```"]):
                if in_steps and steps:
                    break
            if in_steps and line:
                # Numbered step: "1. ...", "2) ..."
                if len(line) > 2 and line[0].isdigit():
                    for sep in ['. ', ') ', ': ', '- ']:
                        if sep in line[:5]:
                            steps.append(line.split(sep, 1)[1].strip())
                            break
                elif line.startswith("-") or line.startswith("•"):
                    steps.append(line[1:].strip())
        
        return steps
    
    def _extract_frame_analysis(self, text: str) -> List[str]:
        """Extract actions from Frame-by-frame analysis."""
        steps = []
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            # Match "Frame N: ..." format
            if line.lower().startswith("frame ") and ":" in line:
                action = line.split(":", 1)[1].strip()
                if action and len(action) > 5:
                    steps.append(action)
        
        return steps
    
    def provide_feedback(self, skill_name: str, success: bool, notes: str = "") -> str:
        """Provide feedback on a learned skill for RL training."""
        self.forge.record_usage(skill_name, success)
        
        reward_signal = "positive" if success else "negative"
        self.trainer.log_interaction(
            task=f"Skill execution: {skill_name}",
            response=notes,
            success=success,
            user_feedback=reward_signal
        )
        
        if success:
            return f"✓ Skill '{skill_name}' marked as successful. Learning reinforced."
        else:
            # Trigger immediate optimization attempt
            opt_result = self._optimize_skill(skill_name, notes or "Task marked as failed.")
            if opt_result:
                 return f"✗ Skill '{skill_name}' failed. Optimization attempted: {opt_result}"
            return f"✗ Skill '{skill_name}' marked as failed. Optimization skipped."

    def _optimize_skill(self, name: str, feedback: str) -> Optional[str]:
        """
        Attempt to optimize/fix a skill using LLM reasoning based on feedback.
        Returns a summary of the change if successful, None otherwise.
        """
        skill = self.forge.get(name)
        if not skill:
            return None
            
        print(f"[*] Optimizing skill '{name}' based on feedback: {feedback}")
        
        current_steps = "\n".join(skill.steps)
        
        # Construct optimization prompt
        prompt_content = f"""You are an expert macOS automation engineer.
I need you to FIX or OPTIMIZE a recorded skill based on user feedback.

SKILL INFO:
Name: "{name}"
Description: {skill.description}

CURRENT LOGIC (Steps/Code):
------------------------------------------------
{current_steps}
------------------------------------------------

USER FEEDBACK / FAILURE REASON:
"{feedback}"

YOUR TASK:
Analyze why the skill failed or how it can be improved.
Rewrite the logic (Steps or AppleScript) to address the feedback.
- If it's an AppleScript, ensure syntax is correct and timeouts are handled.
- If it's manual steps, make them more precise.
- You typically want to make the skill MORE ROBUST.

OUTPUT FORMAT:
Provide the NEW COMPLETE version of the steps/code.
Use the same format as the original (e.g. if it was AppleScript, return AppleScript).
Wrap code in ```applescript``` if applicable.
"""

        messages = [{"role": "user", "content": prompt_content}]
        
        try:
            # Use gpt-4o for code reasoning
            response = self.router.chat(
                messages=messages,
                model="gpt-4o",
                max_tokens=2000,
                temperature=0.2
            )
            
            new_content = response["content"]
            
            # Extract new steps
            new_steps = self._extract_steps(new_content)
            
            # Fallback if extraction fails but content looks like code
            if not new_steps and "```" in new_content:
                # Extract code block content directly
                import re
                code_match = re.search(r"```(?:applescript)?(.*?)```", new_content, re.DOTALL)
                if code_match:
                     new_steps = [line.strip() for line in code_match.group(1).split('\n') if line.strip()]

            if not new_steps:
                print("[-] Optimization failed: Could not extract steps from response.")
                return None
                
            # Compare length/changes roughly
            if new_steps == skill.steps:
                print("[-] Optimization resulted in identical steps.")
                return None
                
            # Apply update
            self.forge.update_skill_logic(
                name=name,
                new_steps=new_steps,
                metadata_update={
                    "last_optimization_reason": feedback,
                    "last_optimized_at": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
            )
            
            return "Skill logic updated based on feedback."
            
        except Exception as e:
            print(f"[-] Optimization error: {e}")
            return None


# Global instance
_learner: Optional[VisualLearner] = None


def get_visual_learner() -> VisualLearner:
    """Get or create global visual learner."""
    global _learner
    if _learner is None:
        _learner = VisualLearner()
    return _learner

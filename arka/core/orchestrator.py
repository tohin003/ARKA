"""
ARKA Orchestrator
Main agent that coordinates sub-agents and manages task flow.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

from arka.config import get_config, Config
from arka.core.model_router import ModelRouter
from arka.core.token_tracker import TokenTracker
from arka.prompt_loader import get_prompt_loader
from arka.agents.planner import PlannerAgent, Plan
from arka.agents.coder import CoderAgent, CodeOutput
from arka.agents.tester import TesterAgent, TestReport
from arka.agents.tester import TesterAgent, TestReport
from arka.agents.debugger import DebuggerAgent, BugFix
from arka.agents.gui_agent import GuiAgent


@dataclass
class TaskResult:
    """Result from a task execution."""
    success: bool
    output: str
    agent: str
    model: str
    tokens_used: int
    duration: float
    error: Optional[str] = None


class Orchestrator:
    """
    Main orchestrator that coordinates sub-agents.
    Decomposes tasks, assigns to appropriate agents, and aggregates results.
    """
    
    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        tracker: Optional[TokenTracker] = None,
        config: Optional[Config] = None,
        tool_executor: Optional[Any] = None,
    ):
        self.config = config or get_config()
        self.router = router or ModelRouter(self.config)
        self.tracker = tracker or TokenTracker(self.config)
        self.prompt_loader = get_prompt_loader()
        
        from arka.tools.tool_executor import get_tool_executor
        self.tool_executor = tool_executor or get_tool_executor()
        
        from arka.memory.memory_client import MemoryClient
        self.memory = MemoryClient()
        
        from arka.training.rl_trainer import get_trainer
        self.trainer = get_trainer()
        
        # Initialize sub-agents
        self.planner = PlannerAgent(self.router, self.tracker, tool_executor=self.tool_executor)
        self.coder = CoderAgent(self.router, self.tracker, tool_executor=self.tool_executor)
        self.tester = TesterAgent(self.router, self.tracker, tool_executor=self.tool_executor)
        self.debugger = DebuggerAgent(self.router, self.tracker, tool_executor=self.tool_executor)
        self.gui = GuiAgent(self.router, self.tracker, tool_executor=self.tool_executor)
        
        self.history: List[Dict[str, Any]] = []
        self._agent_map = {
            "planner": self.planner,
            "coder": self.coder,
            "tester": self.tester,
            "debugger": self.debugger,
            "gui": self.gui,
        }
    
    def chat(self, message: str, use_agents: bool = True) -> str:
        """
        Process a user message and return response.
        
        Args:
            message: User's message
            use_agents: Whether to use sub-agents for complex tasks
            
        Returns:
            Response string
        """
        self.history.append({"role": "user", "content": message})
        
        # Simple check for coding-related tasks
        message_lower = message.lower()
        is_coding_task = any(word in message_lower for word in [
            "write", "code", "create", "build", "implement", "function",
            "class", "script", "program", "fix", "debug", "test"
        ])
        
        # Check for GUI/Web tasks
        is_gui_task = any(word in message_lower for word in [
            "click", "open", "browser", "search", "navigate", "website", 
            "app", "music", "play", "type", "scroll", "find"
        ])
        
        if use_agents:
            if is_coding_task:
                response = self._execute_with_agents(message)
            elif is_gui_task:
                 # Route directly to GUI agent for simpler requests, or plan if complex
                 if len(message.split()) > 100: # Heuristic for complexity
                     response = self._execute_with_agents(message)
                 else:
                     result = self.gui.process(message)
                     response = result.output if hasattr(result, 'output') else str(result)
            else:
                response = self._direct_chat(message)
        else:
            response = self._direct_chat(message)
        
        self.history.append({"role": "assistant", "content": response})
        return response
    
    def _direct_chat(self, message: str) -> str:
        """Chat directly using tools (System Control)."""
        import json
        from arka.tools.tool_executor import get_tool_executor, TOOL_DEFINITIONS
        tool_executor = get_tool_executor()
        
        # Retrieve persona and relevant context
        persona = self.memory.get_persona()
        context = self.memory.search(message, limit=3)
        context_str = "\n".join([c.content for c in context]) if context else ""
        
        system_prompt = self.prompt_loader.get_core_prompt()
        if persona:
             system_prompt += f"\n\n## User Persona\n{persona}"
        
        # Build initial messages path
        messages = [
            {"role": "system", "content": system_prompt},
            *self.history[-10:],
        ]
        
        # Inject memory context into the user message
        if context_str:
            # We assume messages[-1] is the user message (from history)
            # Create a copy to avoid mutating global history permanently if needed,
            # but for now mutating the list item we just created/extracted is fine
            # as long as we constructed the list fresh.
            # However, self.history[-1] is a reference. Mutating it persists memory in history?
            # Actually, modifying the content for THIS turn is good.
            # But simpler transparency: just append a system message? No, user message is stronger using context.
            # Let's clone the message dict to avoid modifying self.history
             last_msg = messages[-1].copy()
             last_msg["content"] += f"\n\n[Relevant Memory context]:\n{context_str}"
             messages[-1] = last_msg
        
        # Tool Use Loop (Max 5 turns)
        params = {
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
        }
        
        final_content = ""
        
        for _ in range(5):
            # We construct the messages list dynamically to include tool results for this turn
            response = self.router.chat(messages=messages, **params)
            
            # Record usage
            self.tracker.record_usage(
                model=response["model"],
                input_tokens=response["input_tokens"],
                output_tokens=response["output_tokens"],
                agent="orchestrator",
            )
            
            content = response.get("content")
            tool_calls = response.get("tool_calls")
            
            # Append assistant response (even if null content but has tool calls)
            assistant_msg = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)
            
            if tool_calls:
                # Execute tools
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except:
                        args = {}
                    
                    # Execute
                    result_str = tool_executor.execute(tool_name, args)
                    
                    # Append tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str
                    })
                
                # Continue loop to get AI interpretation of results
                continue
            
            # If no tool calls, we are done
            final_content = content
            break
            
        # Log to RL trainer (uncategorized initially)
        self.trainer.log_interaction(
            task=message,
            response=final_content or "No response",
            success=True,
            tokens_used=response["output_tokens"]
        )
        
        return final_content or "I executed the actions but have no specific response."
    
    def _execute_with_agents(self, task: str) -> str:
        """Execute task using sub-agents."""
        results = []
        
        # Step 1: Plan the task
        results.append(f"{self.planner.display_name} Planning task...")
        plan = self.planner.process(task)
        results.append(f"  ✓ Created plan with {len(plan.steps)} steps")
        
        # Step 2: Execute each step
        for step in plan.steps:
            agent = self._agent_map.get(step.agent, self.coder)
            results.append(f"\n{agent.display_name} {step.name}...")
            
            if step.agent == "coder":
                output = self.coder.process(step.description)
                results.append(f"  ✓ Generated code")
                if output.code:
                    results.append(f"```{output.language}\n{output.code}\n```")
            
            elif step.agent == "tester":
                # Get last code output for testing
                test_result = self.tester.process(step.description)
                status = "✓ Approved" if test_result.approved else "⚠ Needs review"
                results.append(f"  {status}")
            
            elif step.agent == "debugger":
                fix = self.debugger.process(step.description)
                results.append(f"  ✓ Analysis complete")
            
            elif step.agent == "gui":
                output = self.gui.process(step.description)
                results.append(f"  ✓ GUI Action Complete: {output}")

            else:
                # Default to coder
                output = self.coder.process(step.description)
                results.append(f"  ✓ Completed")
        
        return "\n".join(results)
    
    def code(self, task: str, context: Optional[str] = None) -> CodeOutput:
        """Direct access to coder agent."""
        return self.coder.process(task, context)
    
    def test(self, code: str, requirements: Optional[str] = None) -> TestReport:
        """Direct access to tester agent."""
        return self.tester.process(code, requirements)
    
    def debug(self, code: str, error: Optional[str] = None) -> BugFix:
        """Direct access to debugger agent."""
        return self.debugger.process(code, error)
    
    def plan(self, task: str) -> Plan:
        """Direct access to planner agent."""
        return self.planner.process(task)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "history_length": len(self.history),
            "current_model": self.router.current_model,
            "agents": {
                "planner": self.planner.model,
                "coder": self.coder.model,
                "tester": self.tester.model,
                "debugger": self.debugger.model,
            },
            "usage": self.tracker.get_detailed_stats(),
        }

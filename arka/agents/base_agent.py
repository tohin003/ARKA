"""
ARKA Base Agent
Abstract base class for all sub-agents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import time

from arka.core.model_router import ModelRouter
from arka.core.token_tracker import TokenTracker
from arka.prompt_loader import get_prompt_loader


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    """A message in agent conversation."""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    """Result from agent execution."""
    success: bool
    output: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    duration: float = 0.0
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for all ARKA sub-agents.
    Provides common functionality for LLM interaction and tracking.
    """
    
    # Override in subclasses
    AGENT_TYPE: str = "base"
    AGENT_ICON: str = "🤖"
    
    def __init__(
        self,
        router: ModelRouter,
        tracker: TokenTracker,
        model_override: Optional[str] = None,
        tool_executor: Optional[Any] = None,
    ):
        self.router = router
        self.tracker = tracker
        from arka.tools.tool_executor import get_tool_executor
        self.tool_executor = tool_executor or get_tool_executor()
        self.prompt_loader = get_prompt_loader()
        
        # Model for this agent
        self._model = model_override or router.get_model_for_agent(self.AGENT_TYPE)
        
        # Conversation history for this agent
        self.messages: List[AgentMessage] = []
        self.status = AgentStatus.IDLE
    
    @property
    def model(self) -> str:
        """Get the model used by this agent."""
        return self._model
    
    @property
    def display_name(self) -> str:
        """Get display name with icon and model."""
        return f"{self.AGENT_ICON} [{self.AGENT_TYPE.capitalize()}:{self._model}]"
    
    def get_system_prompt(self, task: Optional[str] = None) -> str:
        """Get the system prompt for this agent."""
        return self.prompt_loader.get_agent_prompt(self.AGENT_TYPE, task)
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.messages.append(AgentMessage(role=role, content=content))
    
    def clear_history(self):
        """Clear conversation history."""
        self.messages.clear()
    
    def _build_messages(self, task: str) -> List[Dict[str, str]]:
        """Build message list for LLM call."""
        messages = [
            {"role": "system", "content": self.get_system_prompt(task)},
        ]
        
        # Add conversation history
        for msg in self.messages[-10:]:  # Keep last 10 messages
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current task
        messages.append({"role": "user", "content": task})
        
        return messages
    
    def execute(self, task: str) -> AgentResult:
        """
        Execute a task and return the result.
        
        Args:
            task: The task description to execute
            
        Returns:
            AgentResult with output and metadata
        """
        self.status = AgentStatus.THINKING
        start_time = time.time()
        
        try:
            messages = self._build_messages(task)
            
            # ReAct Loop: Allow up to 5 turns of tool execution
            final_content = ""
            total_input_tokens = 0
            total_output_tokens = 0
            last_model = self._model
            
            for _ in range(5):
                self.status = AgentStatus.EXECUTING
                
                # Get response with tools
                response = self.router.chat(
                    messages=messages,
                    model=self._model,
                    tools=self.tool_executor.get_tool_definitions(),
                    tool_choice="auto"
                )
                
                start_usage_in = response.get("input_tokens", 0)
                start_usage_out = response.get("output_tokens", 0)
                total_input_tokens += start_usage_in
                total_output_tokens += start_usage_out
                last_model = response.get("model", self._model)
                
                # Record usage immediately
                self.tracker.record_usage(
                    model=last_model,
                    input_tokens=start_usage_in,
                    output_tokens=start_usage_out,
                    agent=self.AGENT_TYPE,
                )
                
                assistant_msg = response.get("content") or ""
                tool_calls = response.get("tool_calls")
                
                # Append assistant message to history
                messages.append({
                    "role": "assistant",
                    "content": assistant_msg,
                    "tool_calls": tool_calls
                })
                
                if not tool_calls:
                    final_content = assistant_msg
                    break
                
                # Execute tools
                for tool_call in tool_calls:
                    import json
                    function_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except:
                        arguments = {}
                        
                    # Execute
                    result_str = self.tool_executor.execute(function_name, arguments)
                    
                    # Append tool result
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": str(result_str)
                    })
            else:
                 final_content = "Target task steps limit reached (5 steps)."

            # Store in history
            self.add_message("user", task)
            self.add_message("assistant", final_content)
            
            self.status = AgentStatus.COMPLETED
            
            # Log to RL trainer
            try:
                from arka.training.rl_trainer import get_trainer
                get_trainer().log_interaction(
                    task=task,
                    response=final_content,
                    success=True,
                    tokens_used=total_output_tokens,
                    metadata={"agent": self.AGENT_TYPE, "model": self._model}
                )
            except Exception:
                pass  # Don't fail execution if logging fails
            
            return AgentResult(
                success=True,
                output=final_content,
                model=last_model,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                duration=time.time() - start_time,
            )
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            
            # Log failure to RL trainer
            try:
                from arka.training.rl_trainer import get_trainer
                get_trainer().log_interaction(
                    task=task,
                    response="",
                    success=False,
                    metadata={"agent": self.AGENT_TYPE, "error": str(e)}
                )
            except Exception:
                pass

            return AgentResult(
                success=False,
                output="",
                model=self._model,
                duration=time.time() - start_time,
                error=str(e),
            )
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """
        Process input according to agent's specialty.
        Override in subclasses.
        """
        pass

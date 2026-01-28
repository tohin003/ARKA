"""
ARKA Model Router
Routes LLM requests to OpenAI API.
Handles model selection, cost tracking, and fallback.
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Generator

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from arka.config import get_config, Config


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    context_limit: int
    cost_per_1k_input: float
    cost_per_1k_output: float


# Model cost table (USD per 1K tokens) - OpenAI models only
MODEL_COSTS = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-5.2-codex": {"input": 0.003, "output": 0.012},  # Optimized for coding
    "o1-preview": {"input": 0.015, "output": 0.06},
    "o1-mini": {"input": 0.003, "output": 0.012},
}


class ModelRouter:
    """
    Routes LLM requests to OpenAI API.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self._openai_client: Optional[Any] = None
        self._current_model: str = self.config.models.default
        
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None and OpenAI is not None:
            api_key = os.environ.get("OPENAI_API_KEY") or self.config.openai.api_key
            if api_key:
                self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client
    
    def reinitialize_client(self):
        """Force reinitialization of the OpenAI client (call after setting API key)."""
        self._openai_client = None
        return self.openai_client is not None
    
    @property
    def current_model(self) -> str:
        """Get currently active model."""
        return self._current_model
    
    @current_model.setter
    def current_model(self, model: str):
        """Set current model with validation."""
        if self._is_valid_model(model):
            self._current_model = model
        else:
            raise ValueError(f"Unknown model: {model}. Available: {self.config.openai.available_models}")
    
    def _is_valid_model(self, model: str) -> bool:
        """Check if model is available."""
        return model in self.config.openai.available_models
    
    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        """Get detailed info about a model."""
        model = model or self._current_model
        costs = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
        context_limit = self.config.tokens.context_limits.get(model, 128000)
        
        return ModelInfo(
            name=model,
            context_limit=context_limit,
            cost_per_1k_input=costs["input"],
            cost_per_1k_output=costs["output"],
        )
    
    def list_models(self) -> List[str]:
        """List all available models."""
        return self.config.openai.available_models
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat completion request to OpenAI.
        
        Returns:
            Dict with keys: content, model, input_tokens, output_tokens
        """
        model = model or self._current_model
        
        if not self._is_valid_model(model):
            raise ValueError(f"Unknown model: {model}")
        
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized. Set OPENAI_API_KEY environment variable.")
        
        params = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        
        # Determine if this is a newer model that uses different API parameters
        is_new_model = any(x in model for x in ['gpt-5', 'o1', 'o3', 'gpt-4.1'])
        
        # Temperature: not supported for o1/o3 reasoning models
        if 'o1' in model or 'o3' in model:
            pass  # Don't add temperature
        else:
            params["temperature"] = temperature
        
        # Token limit: new models use max_completion_tokens, older use max_tokens
        if max_tokens:
            if is_new_model:
                params["max_completion_tokens"] = max_tokens
            else:
                params["max_tokens"] = max_tokens
        
        params.update(kwargs)
        
        response = self.openai_client.chat.completions.create(**params)
        
        if stream:
            return self._handle_stream(response, model)
        
        return {
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls,
            "model": model,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }
    
    def _handle_stream(self, response, model: str) -> Generator[Dict[str, Any], None, None]:
        """Handle streaming response from OpenAI."""
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield {
                    "content": chunk.choices[0].delta.content,
                    "model": model,
                    "done": False,
                }
        yield {"content": "", "model": model, "done": True}
    
    def get_model_for_agent(self, agent_type: str) -> str:
        """Get the configured model for a specific agent type."""
        agent_models = {
            "orchestrator": self.config.models.default,
            "planner": self.config.models.planner,
            "coder": self.config.models.coder,
            "tester": self.config.models.tester,
            "debugger": self.config.models.debugger,
            "memory_manager": self.config.models.memory_manager,
        }
        return agent_models.get(agent_type, self.config.models.default)
    
    def switch_model(self, model: str) -> str:
        """Switch the current model. Returns the new model name."""
        self.current_model = model
        return self._current_model
    
    def get_cost_estimate(self, input_tokens: int, output_tokens: int, model: Optional[str] = None) -> float:
        """Estimate cost for a given token count."""
        model = model or self._current_model
        costs = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
        return (input_tokens / 1000 * costs["input"] + 
                output_tokens / 1000 * costs["output"])

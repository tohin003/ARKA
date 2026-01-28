"""
ARKA Prompt Loader
Loads modular system prompts from markdown files.
"""

from pathlib import Path
from typing import Dict, Optional
import functools


class PromptLoader:
    """
    Loads and caches system prompts from the prompts directory.
    Supports combining multiple prompt modules.
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or Path(__file__).parent / "prompts"
        self._cache: Dict[str, str] = {}
    
    @functools.lru_cache(maxsize=32)
    def load(self, *prompt_paths: str) -> str:
        """
        Load and combine multiple prompt files.
        
        Args:
            *prompt_paths: Relative paths like "core/identity", "agents/coder"
            
        Returns:
            Combined prompt text
        """
        parts = []
        
        for path in prompt_paths:
            content = self._load_single(path)
            if content:
                parts.append(content)
        
        return "\n\n---\n\n".join(parts)
    
    def _load_single(self, prompt_path: str) -> str:
        """Load a single prompt file."""
        # Check cache
        if prompt_path in self._cache:
            return self._cache[prompt_path]
        
        # Build file path
        file_path = self.prompts_dir / f"{prompt_path}.md"
        
        if not file_path.exists():
            return ""
        
        # Load and cache
        content = file_path.read_text()
        self._cache[prompt_path] = content
        return content
    
    def get_core_prompt(self) -> str:
        """Get the combined core prompts (identity + style + policy)."""
        return self.load(
            "core/identity",
            "core/tone_and_style",
            "core/tool_usage_policy",
        )
    
    def get_agent_prompt(self, agent_type: str, task: Optional[str] = None) -> str:
        """
        Get prompt for a specific agent type.
        Combines core prompts with agent-specific prompt.
        Optionally injects learned patterns relevant to the task.
        """
        core = self.get_core_prompt()
        agent = self._load_single(f"agents/{agent_type}")
        
        if agent:
            prompt = f"{core}\n\n---\n\n{agent}"
        else:
            prompt = core
            
        # Inject learned examples if available
        if task:
            try:
                from arka.training.rl_trainer import get_trainer
                trainer = get_trainer()
                examples = trainer.get_relevant_examples(task, limit=3)
                
                if examples:
                    learned_section = "\n\n## Learned Patterns (Successful Interactions)\n"
                    # Add disclaimer
                    learned_section += "> [!NOTE] These are historical examples of similar successful tasks.\n"
                    
                    for i, ex in enumerate(examples, 1):
                        learned_section += f"\nExample {i}:\nUser: {ex['state']['task']}\nAssistant: {ex['action']}\n"
                    
                    prompt += learned_section
            except Exception:
                pass
            
        return prompt
    
    def reload(self):
        """Clear cache and reload prompts."""
        self._cache.clear()
        self.load.cache_clear()
    
    def list_available(self) -> Dict[str, list]:
        """List all available prompts by category."""
        result = {"core": [], "agents": [], "tools": [], "skills": []}
        
        for category in result.keys():
            category_dir = self.prompts_dir / category
            if category_dir.exists():
                result[category] = [
                    f.stem for f in category_dir.glob("*.md")
                ]
        
        return result


# Global loader instance
_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get or create global prompt loader."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader

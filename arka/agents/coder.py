"""
ARKA Coder Agent
Generates and modifies code using GPT-5.2-Codex.
"""

from dataclasses import dataclass
from typing import Optional, List
import re

from arka.agents.base_agent import BaseAgent, AgentResult


@dataclass
class CodeOutput:
    """Output from the coder agent."""
    code: str
    language: str
    filename: Optional[str]
    explanation: str
    usage_example: Optional[str] = None


class CoderAgent(BaseAgent):
    """
    Coding agent powered by GPT-5.2-Codex.
    Generates high-quality, production-ready code.
    """
    
    AGENT_TYPE = "coder"
    AGENT_ICON = "🔧"
    
    def process(self, task: str, context: Optional[str] = None) -> CodeOutput:
        """
        Generate code for the given task.
        
        Args:
            task: Code generation task
            context: Optional context (existing code, requirements)
            
        Returns:
            CodeOutput with generated code
        """
        # Build prompt with context
        prompt = task
        if context:
            prompt = f"{task}\n\nContext:\n```\n{context}\n```"
        
        result = self.execute(prompt)
        
        if not result.success:
            return CodeOutput(
                code="# Error generating code",
                language="python",
                filename=None,
                explanation=f"Error: {result.error}",
            )
        
        return self._parse_code_output(result.output)
    
    def _parse_code_output(self, output: str) -> CodeOutput:
        """Parse LLM output to extract code blocks."""
        # Find code blocks
        code_pattern = r'```(\w+)?\n(.*?)```'
        matches = list(re.finditer(code_pattern, output, re.DOTALL))
        
        if matches:
            # Use the first code block
            first_match = matches[0]
            language = first_match.group(1) or "python"
            code = first_match.group(2).strip()
            
            # Try to find filename
            filename = None
            filename_pattern = r'`([^`]+\.\w+)`'
            filename_match = re.search(filename_pattern, output)
            if filename_match:
                filename = filename_match.group(1)
            
            # Get explanation (text before first code block)
            explanation = output[:first_match.start()].strip()
            
            # Find usage example (often second code block)
            usage_example = None
            if len(matches) > 1:
                usage_example = matches[1].group(2).strip()
            
            return CodeOutput(
                code=code,
                language=language,
                filename=filename,
                explanation=explanation,
                usage_example=usage_example,
            )
        
        # No code block found, return raw output
        return CodeOutput(
            code=output,
            language="python",
            filename=None,
            explanation="",
        )
    
    def modify_code(self, original_code: str, instructions: str) -> CodeOutput:
        """
        Modify existing code based on instructions.
        
        Args:
            original_code: The code to modify
            instructions: What changes to make
            
        Returns:
            CodeOutput with modified code
        """
        prompt = f"""Modify the following code according to these instructions:

Instructions: {instructions}

Original Code:
```
{original_code}
```

Provide the modified code with explanation of changes."""
        
        return self.process(prompt)
    
    def explain_code(self, code: str) -> str:
        """
        Get an explanation of what code does.
        
        Args:
            code: The code to explain
            
        Returns:
            Explanation string
        """
        prompt = f"""Explain what this code does in simple terms:

```
{code}
```

Provide a clear, concise explanation."""
        
        result = self.execute(prompt)
        return result.output if result.success else f"Error: {result.error}"

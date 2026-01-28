"""
ARKA Debugger Agent
Identifies and fixes bugs using GPT-5.2-Codex.
"""

from dataclasses import dataclass
from typing import Optional

from arka.agents.base_agent import BaseAgent, AgentResult


@dataclass
class BugFix:
    """A bug fix result."""
    original_code: str
    fixed_code: str
    root_cause: str
    explanation: str
    prevention_tips: str


class DebuggerAgent(BaseAgent):
    """
    Debugging agent powered by GPT-5.2-Codex.
    Identifies root causes and fixes bugs.
    """
    
    AGENT_TYPE = "debugger"
    AGENT_ICON = "🐛"
    
    def process(
        self,
        code: str,
        error: Optional[str] = None,
        description: Optional[str] = None,
    ) -> BugFix:
        """
        Debug code and provide a fix.
        
        Args:
            code: The buggy code
            error: Error message or stack trace
            description: Description of the expected behavior
            
        Returns:
            BugFix with fixed code and explanation
        """
        prompt = f"""Debug this code:

```
{code}
```
"""
        if error:
            prompt += f"\nError message:\n```\n{error}\n```\n"
        
        if description:
            prompt += f"\nExpected behavior: {description}\n"
        
        prompt += """
Provide:
1. Root cause analysis
2. Fixed code
3. Explanation of the fix
4. How to prevent this bug in the future"""
        
        result = self.execute(prompt)
        
        if not result.success:
            return BugFix(
                original_code=code,
                fixed_code=code,
                root_cause=f"Error during debugging: {result.error}",
                explanation="Could not analyze the code",
                prevention_tips="",
            )
        
        return self._parse_bug_fix(code, result.output)
    
    def _parse_bug_fix(self, original: str, output: str) -> BugFix:
        """Parse LLM output into BugFix."""
        import re
        
        # Extract fixed code from code blocks
        code_pattern = r'```\w*\n(.*?)```'
        matches = list(re.finditer(code_pattern, output, re.DOTALL))
        
        fixed_code = matches[0].group(1).strip() if matches else original
        
        # Extract sections
        root_cause = ""
        explanation = ""
        prevention = ""
        
        sections = output.split("\n\n")
        for section in sections:
            section_lower = section.lower()
            if "root cause" in section_lower or "cause" in section_lower:
                root_cause = section
            elif "explanation" in section_lower or "fix" in section_lower:
                explanation = section
            elif "prevent" in section_lower or "future" in section_lower:
                prevention = section
        
        return BugFix(
            original_code=original,
            fixed_code=fixed_code,
            root_cause=root_cause or "See explanation",
            explanation=explanation or output,
            prevention_tips=prevention or "",
        )
    
    def analyze_error(self, error: str, context: Optional[str] = None) -> str:
        """
        Analyze an error message without code.
        
        Args:
            error: Error message or stack trace
            context: Optional context about what was happening
            
        Returns:
            Analysis and suggestions
        """
        prompt = f"""Analyze this error:

```
{error}
```
"""
        if context:
            prompt += f"\nContext: {context}\n"
        
        prompt += """
Explain:
1. What this error means
2. Common causes
3. How to fix it"""
        
        result = self.execute(prompt)
        return result.output if result.success else f"Error: {result.error}"

"""
ARKA Planner Agent
Decomposes complex tasks into actionable steps.
"""

from dataclasses import dataclass
from typing import List, Optional
import re

from arka.agents.base_agent import BaseAgent, AgentResult


@dataclass
class PlanStep:
    """A single step in a plan."""
    number: int
    name: str
    agent: str
    description: str
    expected_output: str


@dataclass
class Plan:
    """A complete task plan."""
    task: str
    prerequisites: List[str]
    steps: List[PlanStep]
    success_criteria: List[str]
    risks: List[str]


class PlannerAgent(BaseAgent):
    """
    Planning agent that decomposes tasks into steps.
    Uses gpt-4o for strategic thinking.
    """
    
    AGENT_TYPE = "planner"
    AGENT_ICON = "⚡"
    
    def process(self, task: str) -> Plan:
        """
        Create a plan for the given task.
        
        Args:
            task: High-level task description
            
        Returns:
            Plan object with steps
        """
        result = self.execute(task)
        
        if not result.success:
            # Return minimal plan on error
            return Plan(
                task=task,
                prerequisites=[],
                steps=[PlanStep(
                    number=1,
                    name="Execute Task",
                    agent="coder",
                    description=task,
                    expected_output="Task completed",
                )],
                success_criteria=["Task is complete"],
                risks=["Error occurred during planning"],
            )
        
        return self._parse_plan(task, result.output)
    
    def _parse_plan(self, task: str, output: str) -> Plan:
        """Parse LLM output into a Plan object."""
        # Simple parsing - extract steps
        steps = []
        # Regex: 1. **Title** (Agent: name) - allow various formats
        # Capture groups: 1=Num, 2=Name, 3=Agent (Optional)
        step_pattern = r'(\d+)\.\s*(?:\*\*)?([^*:\n\(]+)(?:\*\*)?.*?(?:\(Agent:\s*(\w+)\)|Agent:\s*(\w+))?'
        
        # Smart detection context
        task_lower = task.lower()
        gui_keywords = ["browser", "click", "open", "play", "app", "navigate", "search", "youtube", "music", "spotify", "comet"]
        is_gui_task = any(kw in task_lower for kw in gui_keywords)
        default_agent = "gui" if is_gui_task else "coder"

        for match in re.finditer(step_pattern, output, re.DOTALL | re.IGNORECASE):
            # Agent can be in group 3 or 4 depending on which part of regex matched
            raw_agent = match.group(3) or match.group(4)
            agent = raw_agent.lower() if raw_agent else default_agent

            steps.append(PlanStep(
                number=int(match.group(1)),
                name=match.group(2).strip(),
                agent=agent,
                description=match.group(2).strip(),
                expected_output="Step completed",
            ))
        
        # If no structured steps found, create a single step with smart routing
        if not steps:
            
            steps = [PlanStep(
                number=1,
                name="Execute Task",
                agent=target_agent,
                description=task,
                expected_output="Task completed",
            )]
        
        return Plan(
            task=task,
            prerequisites=[],
            steps=steps,
            success_criteria=["All steps completed successfully"],
            risks=[],
        )

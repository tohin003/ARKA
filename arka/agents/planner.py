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
        step_pattern = r'(\d+)\.\s*\*\*([^*]+)\*\*.*?Agent:\s*(\w+)'
        
        for match in re.finditer(step_pattern, output, re.DOTALL):
            steps.append(PlanStep(
                number=int(match.group(1)),
                name=match.group(2).strip(),
                agent=match.group(3).lower(),
                description=match.group(2).strip(),
                expected_output="Step completed",
            ))
        
        # If no structured steps found, create a single step
        if not steps:
            steps = [PlanStep(
                number=1,
                name="Execute Task",
                agent="coder",
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

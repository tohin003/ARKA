"""
ARKA Tester Agent
Validates code and runs tests using gpt-4o-mini.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

from arka.agents.base_agent import BaseAgent, AgentResult


class TestStatus(Enum):
    """Test result status."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class TestCase:
    """A single test case."""
    name: str
    status: TestStatus
    details: str = ""


@dataclass
class TestReport:
    """Complete test report."""
    tests: List[TestCase] = field(default_factory=list)
    coverage: Optional[float] = None
    issues: List[str] = field(default_factory=list)
    approved: bool = False
    
    @property
    def passed(self) -> int:
        return sum(1 for t in self.tests if t.status == TestStatus.PASS)
    
    @property
    def failed(self) -> int:
        return sum(1 for t in self.tests if t.status == TestStatus.FAIL)


class TesterAgent(BaseAgent):
    """
    Testing agent that validates code.
    Uses gpt-4o-mini for cost-effective validation.
    """
    
    AGENT_TYPE = "tester"
    AGENT_ICON = "🧪"
    
    def process(self, code: str, requirements: Optional[str] = None) -> TestReport:
        """
        Test the given code.
        
        Args:
            code: Code to test
            requirements: Optional requirements to validate against
            
        Returns:
            TestReport with results
        """
        prompt = f"""Review and test this code:

```
{code}
```
"""
        if requirements:
            prompt += f"\nRequirements:\n{requirements}\n"
        
        prompt += """
Generate test cases and validate the code. Report:
1. Any bugs or issues found
2. Whether the code meets requirements
3. Code quality assessment
4. Your verdict: APPROVED, NEEDS REVIEW, or REJECTED"""
        
        result = self.execute(prompt)
        
        if not result.success:
            return TestReport(
                tests=[TestCase("execution", TestStatus.ERROR, str(result.error))],
                approved=False,
            )
        
        return self._parse_test_report(result.output)
    
    def _parse_test_report(self, output: str) -> TestReport:
        """Parse LLM output into TestReport."""
        output_lower = output.lower()
        
        # Determine approval status
        approved = "approved" in output_lower and "rejected" not in output_lower
        
        # Extract any issues mentioned
        issues = []
        if "issue" in output_lower or "bug" in output_lower or "error" in output_lower:
            # Simple extraction - could be more sophisticated
            issues.append("Issues found in code review")
        
        # Create a basic test case based on review
        tests = [
            TestCase(
                name="code_review",
                status=TestStatus.PASS if approved else TestStatus.FAIL,
                details=output[:200] + "..." if len(output) > 200 else output,
            )
        ]
        
        return TestReport(
            tests=tests,
            issues=issues,
            approved=approved,
        )
    
    def generate_tests(self, code: str) -> str:
        """
        Generate pytest test cases for code.
        
        Args:
            code: Code to generate tests for
            
        Returns:
            Generated test code
        """
        prompt = f"""Generate pytest test cases for this code:

```
{code}
```

Include:
- Unit tests for each function
- Edge case tests
- Mock any external dependencies
- Use descriptive test names"""
        
        result = self.execute(prompt)
        return result.output if result.success else f"# Error: {result.error}"

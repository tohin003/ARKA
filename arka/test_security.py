
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from arka.core.security import SecurityManager, SecurityLevel
from arka.tools.tool_executor import ToolExecutor

class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.sec = SecurityManager()
        self.executor = ToolExecutor()
        
    def test_whitelist(self):
        print("\nTesting Whitelist...")
        self.assertEqual(self.sec.check_command("ls -la"), SecurityLevel.SAFE)
        self.assertEqual(self.sec.check_command("echo hello"), SecurityLevel.SAFE)
        self.assertEqual(self.sec.check_command("git status"), SecurityLevel.SAFE)
        print("✓ Whitelisted commands are SAFE")

    def test_dangerous(self):
        print("\nTesting Dangerous Commands...")
        self.assertEqual(self.sec.check_command("rm -rf /"), SecurityLevel.CONFIRMATION_REQUIRED)
        # Assuming we didn't add sudo explicitly to whitelist, it should be dangerous/confirmation
        self.assertEqual(self.sec.check_command("sudo echo hi"), SecurityLevel.CONFIRMATION_REQUIRED) 
        print("✓ Dangerous commands require CONFIRMATION")
        
    def test_blocked(self):
        print("\nTesting Blocked Commands...")
        self.assertEqual(self.sec.check_command(":(){ :|:& };:"), SecurityLevel.BLOCKED)
        print("✓ Blocked commands are BLOCKED")
        
    def test_unknown(self):
        print("\nTesting Unknown Commands...")
        self.assertEqual(self.sec.check_command("random_binary -flag"), SecurityLevel.CONFIRMATION_REQUIRED)
        print("✓ Unknown commands require CONFIRMATION")
        
    @patch("rich.prompt.Confirm.ask")
    def test_executor_interception_denied(self, mock_ask):
        print("\nTesting Executor Interception (User Denies)...")
        # Simulate user saying "No"
        mock_ask.return_value = False
        
        result = self.executor.execute("run_shell", {"command": "rm -rf test"})
        self.assertEqual(result, "Action blocked by user.")
        print("✓ Executor blocked dangerous command when user denied")
        
    @patch("rich.prompt.Confirm.ask")
    @patch("arka.tools.system_controller.SystemController.run_shell") # Mock actual execution
    def test_executor_interception_allowed(self, mock_run, mock_ask):
        print("\nTesting Executor Interception (User Allows)...")
        # Simulate user saying "Yes"
        mock_ask.return_value = True
        mock_run.return_value = MagicMock(success=True, output="Deleted")
        
        result = self.executor.execute("run_shell", {"command": "rm -rf test"})
        self.assertEqual(result, "Deleted")
        print("✓ Executor allowed dangerous command when user approved")

if __name__ == '__main__':
    unittest.main()

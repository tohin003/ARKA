
import sys
from unittest.mock import MagicMock

# Mock dependencies requires for import
sys.modules["playwright.sync_api"] = MagicMock()
sys.modules["pyautogui"] = MagicMock()
sys.modules["PIL"] = MagicMock()

from arka.core.orchestrator import Orchestrator
from arka.tools.tool_executor import get_tool_executor
from arka.agents.gui_agent import GuiAgent

def verify():
    print("Verifying GUI Agent Wiring...")
    
    # 1. Check Tool Executor
    print("1. Checking Tool Definitions...")
    executor = get_tool_executor()
    tools = {t["function"]["name"] for t in executor.get_tool_definitions()}
    required = {"vision_click", "web_navigate", "web_click", "open_application"}
    missing = required - tools
    if missing:
        print(f"❌ Missing tools: {missing}")
        return False
    print("✅ All GUI tools present.")
    
    # 2. Check Orchestrator
    print("2. Checking Orchestrator Integration...")
    orch = Orchestrator()
    if "gui" not in orch._agent_map:
        print("❌ GuiAgent not in Orchestrator agent map")
        return False
    
    if not isinstance(orch.gui, GuiAgent):
         print("❌ orch.gui is not an instance of GuiAgent")
         return False
         
    print("✅ Orchestrator has GuiAgent.")
    
    print("\nSUCCESS: All wiring correct.")
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)

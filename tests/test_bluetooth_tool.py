
import sys
import os
sys.path.append(os.getcwd())

from arka.tools.bluetooth_tool import BluetoothTool

def test_bt():
    print("Testing Bluetooth Tool...")
    tool = BluetoothTool()
    
    # Test List
    res = tool.execute("list")
    if res.success:
        print(f"✅ List Success:\n{res.output}")
    else:
        print(f"❌ List Failed: {res.error}")
        
    # Helper Resolution Test (Mock)
    # We can't connect without a real device name and disrupting user.
    # But if List works, the parsing logic works.

if __name__ == "__main__":
    test_bt()


import sys
import os
sys.path.append(os.getcwd())

from arka.tools.audio_tool import AudioTool

def test_audio():
    print("Testing Audio Tool...")
    tool = AudioTool()
    
    # Test Get
    res = tool.execute("get_volume")
    if res.success:
        print(f"✅ Audio Get Success: {res.output}")
    else:
        print(f"❌ Audio Failed: {res.error}")

if __name__ == "__main__":
    test_audio()

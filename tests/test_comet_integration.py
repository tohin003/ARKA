
import sys
import os

# Ensure we can import arka
sys.path.append(os.getcwd())

from arka.core.browser_manager import BrowserManager

def test_comet_integration():
    print("🔌 Attempting to assume control of Comet Browser (Port 9222)...")
    
    manager = BrowserManager()
    
    # 1. Connect
    success = manager.connect_external(port=9222)
    if not success:
        print("❌ Failed to connect via BrowserManager.")
        return
        
    print("✅ Connection Successful!")
    
    # 2. Verify State
    title = manager.get_title()
    print(f"📄 Current Page Title: '{title}'")
    
    # 3. Test DOM Control (The new feature)
    print("\n[DOM Scan] extracting interactive elements...")
    snapshot = manager.get_dom_snapshot()
    
    if snapshot and "Error" not in snapshot:
        # Show specific elements to prove we see them
        # Truncate to avoid spamming log
        preview = "\n".join(snapshot.split("\n")[:5]) 
        print(f"✅ DOM Snapshot Retrieved:\n{preview}\n... (and more)")
    else:
        print(f"❌ DOM Snapshot Failed: {snapshot}")
        
    # Cleanup (Disconnect but don't close Comet)
    # manager.stop() would close the browser. usage of disconnect needed? 
    # BrowserManager.stop() generally closes. 
    # In CDP mode, we might just want to disconnect. Playwright browser.close() usually closes the app.
    # browser.disconnect() is safer.
    # But BrowserManager.stop() calls close().
    # For test, we accept closing or just leave it. 
    # Current Manager implementation calls close().
    # I'll update Manager later to have disconnect(), but for now let's just exit.
    print("Test Complete.")

if __name__ == "__main__":
    test_comet_integration()

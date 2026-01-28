import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from memory_engine import MemoryEngine

# Paths
COMET_HISTORY = os.path.expanduser("~/Library/Application Support/Comet/User Data/Default/History")
CHROME_HISTORY = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/History")
BRAVE_HISTORY = os.path.expanduser("~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History")

class BrowserConnector:
    def __init__(self, memory_engine: MemoryEngine):
        self.memory = memory_engine
        
    def _get_history_path(self):
        # Prioritize Comet, then Chrome, then Brave
        if os.path.exists(COMET_HISTORY):
            return COMET_HISTORY, "Comet"
        if os.path.exists(CHROME_HISTORY):
            return CHROME_HISTORY, "Chrome"
        if os.path.exists(BRAVE_HISTORY):
            return BRAVE_HISTORY, "Brave"
        return None, None

    def sync(self, days_back=7):
        db_path, browser_name = self._get_history_path()
        if not db_path:
            print("No supported browser history found.")
            return

        print(f"--- Syncing Browser History ({browser_name}) ---")
        
        # Copy to tmp to bypass lock
        tmp_path = "/tmp/history_copy"
        try:
            shutil.copy2(db_path, tmp_path)
        except Exception as e:
            print(f"Error copying history file: {e}")
            return

        # Query
        cutoff_date = datetime.now() - timedelta(days=days_back)
        # Chrome/Webkit stores time in microseconds since 1601... this is annoying.
        # Simplified: Just grab last 500 items for now to test.
        
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT url, title, visit_count FROM urls ORDER BY last_visit_time DESC LIMIT 500")
            rows = cursor.fetchall()
            
            for url, title, count in rows:
                if not title or not url:
                    continue
                    
                # Store
                content = f"Visited Page: {title}\nURL: {url}"
                metadata = {
                    "type": "browser_history",
                    "browser": browser_name,
                    "url": url,
                    "title": title
                }
                
                self.memory.upsert_data(
                    content=content,
                    metadata=metadata,
                    source_id=f"history_{url}"
                )
                
        except Exception as e:
            print(f"Error reading DB: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    mem = MemoryEngine()
    conn = BrowserConnector(mem)
    conn.sync()

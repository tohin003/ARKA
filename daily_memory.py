import os
import datetime
from memory_engine import MemoryEngine

MEMORY_DIR = "memories"

class DailyMemory:
    def __init__(self, memory_engine: MemoryEngine = None):
        if not os.path.exists(MEMORY_DIR):
            os.makedirs(MEMORY_DIR)
        self.memory = memory_engine

    def _get_today_file(self):
        today = datetime.date.today().isoformat()
        return os.path.join(MEMORY_DIR, f"{today}.md")

    def log_event(self, category, description):
        """
        Logs an event to the daily file.
        Category: e.g., 'SYSTEM', 'USER', 'BROWSER', 'ACTION'
        """
        timestamp = datetime.datetime.now().strftime("%I:%M %p")
        log_entry = f"- **{timestamp}** [{category}] {description}\n"
        
        file_path = self._get_today_file()
        with open(file_path, "a") as f:
            f.write(log_entry)
        
        # Optional: Print to console for visibility
        print(f"[DailyMemory] {log_entry.strip()}")

    def sync_day(self, date_str=None):
        """
        Ingests a specific day's log into Vector DB.
        date_str: 'YYYY-MM-DD' (defaults to today)
        """
        if not self.memory:
            print("No memory engine provided, skipping sync.")
            return

        target_date = date_str or datetime.date.today().isoformat()
        file_path = os.path.join(MEMORY_DIR, f"{target_date}.md")
        
        if not os.path.exists(file_path):
            print(f"No memory record found for {target_date}")
            return
            
        with open(file_path, "r") as f:
            content = f.read()
            
        # Ingest as a single "Day Summary" or chunk it?
        # For now, ingest the whole day log as one document for broad context,
        # or maybe chunk by hour if it gets huge.
        
        metadata = {
            "type": "daily_log",
            "date": target_date,
            "source": "daily_memory"
        }
        
        self.memory.upsert_data(
            content=content,
            metadata=metadata,
            source_id=f"memory_{target_date}"
        )
        print(f"Synced daily memory for {target_date}")

if __name__ == "__main__":
    # Test
    # mem = MemoryEngine()
    dm = DailyMemory() # Pass mem to enable sync
    dm.log_event("TEST", "Agent initialized daily memory system.")

import os
import pypdf
from memory_engine import MemoryEngine

RESUME_DIR = "/Users/xyx/Documents/DESKTOP/Resumes"

class ResumeConnector:
    def __init__(self, memory_engine: MemoryEngine):
        self.memory = memory_engine
    
    def extract_text_from_pdf(self, file_path):
        try:
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return None

    def sync(self):
        print(f"--- Syncing Resumes from {RESUME_DIR} ---")
        if not os.path.isdir(RESUME_DIR):
            print(f"Directory not found: {RESUME_DIR}")
            return

        for root, _, files in os.walk(RESUME_DIR):
            for file in files:
                if file.lower().endswith(".pdf"):
                    full_path = os.path.join(root, file)
                    print(f"Processing: {file}")
                    
                    content = self.extract_text_from_pdf(full_path)
                    if content:
                        # Construct Metadata
                        metadata = {
                            "type": "resume",
                            "filename": file,
                            "path": full_path,
                            "timestamp": os.path.getmtime(full_path)
                        }
                        
                        # Upsert
                        self.memory.upsert_data(
                            content=content,
                            metadata=metadata,
                            source_id=f"file_{file}"
                        )

if __name__ == "__main__":
    # Test run
    mem = MemoryEngine() # Will initialize BGE-M3
    connector = ResumeConnector(mem)
    connector.sync()

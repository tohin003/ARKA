import os
import pypdf
import sys
from pathlib import Path

# Add project root to path to ensure arka modules are found
sys.path.append(os.getcwd())

try:
    from arka.memory.memory_client import get_memory
except ImportError:
    # If running as a script from root, this might be needed
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from arka.memory.memory_client import get_memory

RESUME_DIR = "/Users/xyx/Documents/DESKTOP/Resumes"

def extract_text_from_pdf(file_path):
    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return None

def ingest_resumes():
    mem = get_memory()
    # mem._ensure_initialized() # Accessed via public methods now
    
    print(f"--- Ingesting Resumes from {RESUME_DIR} ---")
    if not os.path.isdir(RESUME_DIR):
        print(f"Directory not found: {RESUME_DIR}")
        return

    count = 0
    for root, _, files in os.walk(RESUME_DIR):
        for file in files:
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                print(f"Processing: {file}")
                
                content = extract_text_from_pdf(full_path)
                if content:
                    # Construct Metadata
                    metadata = {
                        "type": "resume",
                        "filename": file,
                        "path": full_path,
                        "timestamp": os.path.getmtime(full_path)
                    }
                    
                    # Add to memory
                    # Using file path hash or filename as ID could be better for idempotency, 
                    # but for now we follow the simple pattern.
                    memory_id = f"file_{file}"
                    
                    try:
                        mem.add(
                            content=content,
                            metadata=metadata,
                            memory_id=memory_id
                        )
                        print(f"✅ Indexed: {file}")
                        count += 1
                    except Exception as e:
                        print(f"❌ Failed to index {file}: {e}")

    print(f"\nIngestion Complete. Processed {count} resumes.")

if __name__ == "__main__":
    ingest_resumes()

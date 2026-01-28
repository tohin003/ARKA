import os
import sys
from pathlib import Path

# Add CWD to path to import arka modules
sys.path.append(os.getcwd())

try:
    from arka.memory.memory_client import get_memory
except ImportError:
    print("Could not import Arka Memory Client. Make sure you are in the project root.")
    sys.exit(1)

import pypdf
import glob

def migrate():
    print("Initializing Arka Memory Client...")
    mem = get_memory()
    mem._ensure_initialized()
    print(f"Target DB: {mem.persist_dir}")

    # 1. Persona
    persona_path = "persona.md"
    if os.path.exists(persona_path):
        print(f"\nProcessing Persona: {persona_path}")
        with open(persona_path, "r") as f:
            content = f.read()
            mem.add(
                content=content,
                metadata={"type": "persona", "source": "manual"},
                memory_id="persona_main"
            )
            print("✅ Ingested Persona")
    else:
        print("❌ Persona file not found.")

    # 2. Resumes
    resume_dir = "/Users/xyx/Documents/DESKTOP/Resumes"
    if os.path.isdir(resume_dir):
        print(f"\nProcessing Resumes in {resume_dir}...")
        pdf_files = glob.glob(os.path.join(resume_dir, "*.pdf"))
        
        for pdf_file in pdf_files:
            try:
                reader = pypdf.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                filename = os.path.basename(pdf_file)
                mem.add(
                    content=text,
                    metadata={"type": "resume", "filename": filename},
                    memory_id=f"file_{filename}"
                )
                print(f"✅ Ingested: {filename}")
            except Exception as e:
                print(f"❌ Failed to process {pdf_file}: {e}")
    else:
        print(f"❌ Resume directory not found: {resume_dir}")

    print("\nMigration Complete.")
    
    # Verify
    print("\n--- Verification: 'What is my name?' ---")
    results = mem.search("What is my name?", limit=3)
    for res in results:
        print(f"- {res.content[:200]}...")

if __name__ == "__main__":
    migrate()

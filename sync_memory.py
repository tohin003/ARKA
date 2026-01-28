from memory_engine import MemoryEngine
from resume_connector import ResumeConnector
# Will import other connectors here later

def main():
    print("Starting Memory Sync...")
    
    # Initialize Core Engine (Loads Model)
    mem = MemoryEngine()
    
    # 1. Resumes
    print("\n[Connector] Resumes")
    resume_conn = ResumeConnector(mem)
    resume_conn.sync()
    
    # 2. Persona
    print("\n[Connector] Persona")
    persona_path = "/Users/xyx/Documents/DESKTOP/AI_AGENT-V1/persona.md"
    try:
        with open(persona_path, "r") as f:
            content = f.read()
            mem.upsert_data(
                content=content,
                metadata={"type": "persona", "source": "manual"},
                source_id="persona_main"
            )
    except FileNotFoundError:
        print("Persona file not found.")

    # 3. Browser History
    from browser_connector import BrowserConnector
    browser_conn = BrowserConnector(mem)
    browser_conn.sync()
    
    print("\nMemory Sync Complete.")

if __name__ == "__main__":
    main()

from memory_engine import MemoryEngine

def verify():
    print("Initializing Memory Engine...")
    mem = MemoryEngine()
    
    print("\n--- Test 1: Persona (Name) ---")
    results = mem.query_similar("What is my name?")
    print(results['documents'][0])

    print("\n--- Test 2: Resumes (Tohin) ---")
    results = mem.query_similar("Show me details about Tohin's projects or skills", n_results=3)
    # Print first 200 chars to avoid spam
    for doc in results['documents'][0]:
        print(f"- {doc[:200]}...")

    print("\n--- Test 3: Browser History (YouTube) ---")
    results = mem.query_similar("youtube reasoning classes")
    print(results['documents'][0])

if __name__ == "__main__":
    verify()

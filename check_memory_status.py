import chromadb
from chromadb.config import Settings
from pathlib import Path
import os

def check_db(path, collection_name, label):
    print(f"\n--- Checking {label} at {path} ---")
    if not os.path.exists(path):
        print(f"❌ Path does not exist: {path}")
        return

    try:
        client = chromadb.PersistentClient(path=str(path))
        try:
            coll = client.get_collection(collection_name)
            count = coll.count()
            print(f"✅ Collection '{collection_name}' found. Item count: {count}")
            
            if count > 0:
                # Query for name
                results = coll.query(
                    query_texts=["What is my name?"],
                    n_results=1
                )
                print(f"   Query 'What is my name?': {results['documents'][0]}")
            else:
                print("   ⚠️ Collection is empty.")
                
        except Exception as e:
            print(f"   ⚠️ Collection '{collection_name}' not found or error: {e}")
            # List collections
            colls = client.list_collections()
            print(f"   Available collections: {[c.name for c in colls]}")

    except Exception as e:
        print(f"Error accessing DB: {e}")

if __name__ == "__main__":
    # 1. Check the DB we built (Phase 2)
    old_db_path = os.path.abspath("chroma_db")
    check_db(old_db_path, "agent_memory", "OLD Memory (Phase 2)")

    # 2. Check the Arka DB (New Structure)
    arka_db_path = Path.home() / ".arka" / "memory"
    check_db(arka_db_path, "arka_memory", "NEW Arka Memory")

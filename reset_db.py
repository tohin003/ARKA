import chromadb
import shutil
import os

DB_PATH = "chroma_db"

def reset():
    print(f"Resetting Database at {DB_PATH}...")
    
    # Method 1: Delete via Client (Cleaner)
    try:
        client = chromadb.PersistentClient(path=DB_PATH)
        try:
            client.delete_collection("agent_memory")
            print("Deleted existing collection 'agent_memory'.")
        except Exception as e:
            print(f"Collection delete failed (might not exist): {e}")
    except Exception as e:
        print(f"Client connection failed: {e}")

    # Method 2: Force Delete Files (Nuclear option if above fails)
    # shutil.rmtree(DB_PATH, ignore_errors=True)
    # print("Deleted existing DB files.")

if __name__ == "__main__":
    reset()

import chromadb
import os

def setup_chromadb():
    print("Initializing ChromaDB...")
    # Create a persistent client
    # The path will be created if it doesn't exist
    persist_path = os.path.join(os.getcwd(), "chroma_db")
    client = chromadb.PersistentClient(path=persist_path)
    
    collection_name = "agent_memory"
    
    try:
        # Get or create the collection
        collection = client.get_or_create_collection(name=collection_name)
        print(f"Successfully created/retrieved collection: '{collection_name}'")
        print(f"Database path: {persist_path}")
        
        # Verify it's empty or check count
        count = collection.count()
        print(f"Current document count in '{collection_name}': {count}")
        
    except Exception as e:
        print(f"Error setting up ChromaDB: {e}")

if __name__ == "__main__":
    setup_chromadb()

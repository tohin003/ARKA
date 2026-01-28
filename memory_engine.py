import chromadb
from chromadb.utils import embedding_functions
import hashlib

class MemoryEngine:
    def __init__(self, persist_path="chroma_db", collection_name="agent_memory"):
        self.client = chromadb.PersistentClient(path=persist_path)
        
        # Use Ollama for Embeddings (Bypasses Python dependency issues)
        print("Using Ollama Embeddings (nomic-embed-text)...")
        self.embedding_fn = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text"
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_fn
        )

    def upsert_data(self, content, metadata, source_id):
        """
        Upsert data into Vector DB.
        source_id: Unique ID for the document (e.g., file path, url)
        """
        # Create a deterministic ID based on content hash + source
        # This prevents duplicates if content hasn't changed
        content_hash = hashlib.md5(content.encode()).hexdigest()
        doc_id = f"{source_id}_{content_hash}"
        
        # Check if exists (deduplication logic can be enhanced)
        existing = self.collection.get(ids=[doc_id])
        if existing['ids']:
            print(f"Skipping duplicate: {source_id}")
            return

        # Chroma's embedding function handles the generation automatically
        self.collection.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id]
        )
        print(f"Upserted: {source_id}")

    def query_similar(self, query_text, n_results=5):
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

if __name__ == "__main__":
    # Test
    mem = MemoryEngine()
    mem.upsert_data("My name is Tohin.", {"source": "test"}, "test_1")
    print(mem.query_similar("What is my name?"))

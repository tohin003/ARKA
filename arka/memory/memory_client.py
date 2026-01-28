"""
ARKA Memory Client
Minimal memory wrapper for Mem0 and ChromaDB.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float = 0.0


class MemoryClient:
    """
    Memory client for storing and retrieving context.
    Wraps ChromaDB for vector storage.
    """
    
    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = Path(persist_dir) if persist_dir else Path.home() / ".arka" / "memory"
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self._chroma_client = None
        self._collection = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB."""
        if self._initialized:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(self.persist_dir),
                anonymized_telemetry=False,
            ))
            
            self._collection = self._chroma_client.get_or_create_collection(
                name="arka_memory",
                metadata={"hnsw:space": "cosine"},
            )
            
            self._initialized = True
        except ImportError:
            # ChromaDB not installed, use simple file-based fallback
            self._initialized = True
    
    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """
        Add a memory entry.
        
        Args:
            content: The content to remember
            metadata: Optional metadata
            memory_id: Optional custom ID
            
        Returns:
            The ID of the stored memory
        """
        self._ensure_initialized()
        
        import uuid
        memory_id = memory_id or str(uuid.uuid4())
        
        if self._collection:
            self._collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[metadata or {}],
            )
        else:
            # Fallback: save to file
            self._save_to_file(memory_id, content, metadata)
        
        return memory_id
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntry]:
        """
        Search for relevant memories.
        
        Args:
            query: Search query
            limit: Maximum results
            filter_metadata: Optional metadata filter
            
        Returns:
            List of matching MemoryEntry objects
        """
        self._ensure_initialized()
        
        if not self._collection:
            return []
        
        results = self._collection.query(
            query_texts=[query],
            n_results=limit,
            where=filter_metadata,
        )
        
        entries = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                entries.append(MemoryEntry(
                    id=doc_id,
                    content=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    score=1 - results["distances"][0][i] if results["distances"] else 0,
                ))
        
        return entries
    
    def get_all(
        self,
        limit: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntry]:
        """
        Get all memories matching filter.
        """
        self._ensure_initialized()
        
        if not self._collection:
            # Fallback for file mode
            if self.persist_dir.exists():
                import json
                memories_file = self.persist_dir / "memories.json"
                if memories_file.exists():
                    all_memories = []
                    data = json.loads(memories_file.read_text())
                    for mid, m in data.items():
                        # Basic filter implementation for file fallback
                        if filter_metadata:
                            match = True
                            for k, v in filter_metadata.items():
                                if m["metadata"].get(k) != v:
                                    match = False
                                    break
                            if not match:
                                continue
                        
                        all_memories.append(MemoryEntry(
                            id=mid,
                            content=m["content"],
                            metadata=m["metadata"],
                            score=1.0
                        ))
                    return all_memories[:limit] if limit else all_memories
            return []
        
        # ChromaDB get
        results = self._collection.get(
            where=filter_metadata,
            limit=limit,
        )
        
        entries = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                entries.append(MemoryEntry(
                    id=doc_id,
                    content=results["documents"][i] if results["documents"] else "",
                    metadata=results["metadatas"][i] if results["metadatas"] else {},
                    score=1.0, # Direct retrieval has no store
                ))
        
        return entries
    def get_persona(self) -> str:
        """Get consolidated user persona from memory."""
        memories = self.search("user persona details", limit=5, filter_metadata={"type": "persona"})
        if not memories:
            return ""
        
        return "\n".join([f"- {m.content}" for m in memories])

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        self._ensure_initialized()
        
        if self._collection:
            try:
                self._collection.delete(ids=[memory_id])
                return True
            except Exception:
                return False
        return False
    
    def clear(self):
        """Clear all memories."""
        self._ensure_initialized()
        
        if self._chroma_client:
            self._chroma_client.delete_collection("arka_memory")
            self._collection = self._chroma_client.create_collection(
                name="arka_memory",
                metadata={"hnsw:space": "cosine"},
            )
    
    def _save_to_file(self, memory_id: str, content: str, metadata: Optional[Dict]):
        """Fallback file-based storage."""
        import json
        
        memories_file = self.persist_dir / "memories.json"
        
        # Ensure directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        memories = {}
        if memories_file.exists():
            memories = json.loads(memories_file.read_text())
        
        memories[memory_id] = {
            "content": content,
            "metadata": metadata or {},
        }
        
        memories_file.write_text(json.dumps(memories, indent=2))


# Global memory client
_memory: Optional[MemoryClient] = None


def get_memory() -> MemoryClient:
    """Get or create global memory client."""
    global _memory
    if _memory is None:
        _memory = MemoryClient()
    return _memory

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
        self.nodes_file = self.persist_dir / "nodes.json"
        self._ensure_nodes_init()

    def _ensure_nodes_init(self):
        """Ensure default nodes exist."""
        if not self.nodes_file.exists():
            import json
            # Default 'general' node always exists
            self.nodes_file.write_text(json.dumps(["general"]))

    def create_node(self, name: str) -> str:
        """Create a new memory node."""
        import json
        if not self.nodes_file.exists():
            self._ensure_nodes_init()
        
        nodes = json.loads(self.nodes_file.read_text())
        name_clean = name.strip().lower()
        if name_clean not in nodes:
            nodes.append(name_clean)
            self.nodes_file.write_text(json.dumps(nodes))
            return f"Node '{name_clean}' created."
        return f"Node '{name_clean}' already exists."

    def list_nodes(self) -> List[str]:
        """List all available memory nodes."""
        import json
        if not self.nodes_file.exists():
             self._ensure_nodes_init()
        return json.loads(self.nodes_file.read_text())

    def delete_node(self, name: str) -> str:
        """
        Delete a memory node and all its data.
        Cannot delete 'general' node.
        """
        import json
        name = name.lower().strip()
        if name == "general":
            return "Error: Cannot delete 'general' node."
        
        if not self.nodes_file.exists():
             self._ensure_nodes_init()
        
        nodes = json.loads(self.nodes_file.read_text())
        if name not in nodes:
            return f"Error: Node '{name}' does not exist."
            
        # 1. Remove from registry
        nodes.remove(name)
        self.nodes_file.write_text(json.dumps(nodes))
        
        # 2. Delete all memories belonging to this node
        # Using _get_all_from_json + _delete_from_json logic
        all_memories = self._get_all_from_json(limit=10000)
        to_delete = [
            m.id for m in all_memories 
            if m.metadata.get("node") == name
        ]
        
        count = 0
        for mid in to_delete:
            if self.delete(mid):
                count += 1
                
        return f"Node '{name}' deleted. Removed {count} associated memories."
    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB."""
        if self._initialized:
            return
        
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            import os
            
            # Use OpenAI embeddings (no download required, fast API)
            api_key = os.getenv("OPENAI_API_KEY")
            ef = None
            if api_key:
                ef = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name="text-embedding-3-small"
                )
            
            # Use new PersistentClient API (ChromaDB 0.4+)
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir),
            )
            
            self._collection = self._chroma_client.get_or_create_collection(
                name="arka_memory",
                metadata={"hnsw:space": "cosine"},
                embedding_function=ef
            )
            
            self._initialized = True
        except ImportError:
            # ChromaDB not installed, use simple file-based fallback
            self._initialized = True
        except Exception as e:
            # ChromaDB failed (e.g., migration needed), use fallback
            print(f"[Memory] ChromaDB init failed: {e}. Using file fallback.")
            self._initialized = True
    
    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
        node: str = "general"
    ) -> str:
        """
        Add a memory.
        If node != 'general', it adds to BOTH the target node AND 'general' node.
        """
        node = node.lower().strip()
        
        # 1. Add to Target Node
        meta_primary = (metadata or {}).copy()
        meta_primary["node"] = node
        
        # Determine strict ID for primary (or auto-gen)
        # Note: We return the ID of the primary entry
        primary_id = self._add_single_entry(content, meta_primary, memory_id)
        
        # 2. If target is NOT general, Dual Write to General with Link Reference
        if node != "general":
            meta_general = (metadata or {}).copy()
            meta_general["node"] = "general"
            # Add Linked Reference Pointer
            meta_general["ref_node"] = node
            meta_general["ref_id"] = primary_id
            meta_general["is_ref"] = True
            
            # Must use different ID for the copy
            self._add_single_entry(content, meta_general, memory_id=None)
            
        return primary_id

    def _add_single_entry(self, content, metadata, memory_id):
        """Internal helper to add a single entry."""
        self._ensure_initialized()
        import uuid
        memory_id = memory_id or str(uuid.uuid4())
        
        # Ensure timestamp exists
        if "timestamp" not in metadata:
            from datetime import datetime
            metadata["timestamp"] = datetime.now().isoformat()
            
        # Always save to file backup
        self._save_to_file(memory_id, content, metadata)
        
        # Try ChromaDB
        if self._collection:
            try:
                self._collection.add(
                    ids=[memory_id],
                    documents=[content],
                    metadatas=[metadata],
                )
            except Exception:
                pass 
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
        
        # Try ChromaDB first - but only if it has data (avoids slow embedding download)
        if self._collection:
            try:
                # Check if collection has any data before querying
                count = self._collection.count()
                if count > 0:
                    results = self._collection.query(
                        query_texts=[query],
                        n_results=limit,
                        where=filter_metadata,
                    )
                    
                    entries = []
                    if results and results["ids"] and results["ids"][0]:
                        for i, doc_id in enumerate(results["ids"][0]):
                            entries.append(MemoryEntry(
                                id=doc_id,
                                content=results["documents"][0][i] if results["documents"] else "",
                                metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                                score=1 - results["distances"][0][i] if results["distances"] else 0,
                            ))
                        return entries
            except Exception:
                pass  # Fall through to JSON fallback
        
        # Fallback: JSON file-based text search
        return self._search_json_fallback(query, limit, filter_metadata)
    def search_time_aware(self, query: str, window_size: int = 15, max_windows: int = 5, node: str = "general") -> List[MemoryEntry]:
        """
        Sliding Window Search (The "Pyramid" Strategy):
        1. Look at the most recent 'window_size' interactions.
        2. Perform a "deep search" (keyword/relevance check) within that window.
        3. If matches found, RETURN immediately (Context Found).
        4. If not, slide the window back to the past and repeat.
        
        This prioritizes Recency > Relevance.
        """
        # 1. Get all chronological data (Source of Truth)
        all_memories = self._get_all_from_json(limit=1000)
        
        # Filter by Node
        node = node.lower().strip()
        # Default fallback for old data: assume 'general' if node not set
        all_memories = [
            m for m in all_memories 
            if m.metadata.get("node", "general") == node
        ]
        
        all_memories.sort(key=lambda x: x.metadata.get("timestamp", ""), reverse=True)
        
        query_terms = query.lower().split()
        matches = []
        
        # 2. Slide the window
        for i in range(0, min(len(all_memories), window_size * max_windows), window_size):
            window = all_memories[i : i + window_size]
            window_matches = []
            
            # 3. Top-Down Search within Window
            for mem in window:
                content_lower = mem.content.lower()
                # Simple score: count of query terms present
                score = sum(1 for term in query_terms if term in content_lower)
                
                # If significant match (e.g. 30% of terms or single distinct term)
                if score > 0:
                     # Calculate simple density score
                     density = score / len(query_terms)
                     mem.score = density
                     # Threshold: at least 1 term matches
                     window_matches.append(mem)
            
            # 4. If this window has good matches, stop and return them!
            # (We found the answer in recent history, don't look further back)
            if window_matches:
                # Sort by relevance within this time window
                window_matches.sort(key=lambda x: x.score, reverse=True)
                return window_matches
                
        return []
    def _search_json_fallback(
        self,
        query: str,
        limit: int,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntry]:
        """Text-based search in JSON fallback storage."""
        import json
        
        memories_file = self.persist_dir / "memories.json"
        if not memories_file.exists():
            return []
        
        try:
            data = json.loads(memories_file.read_text())
        except Exception:
            return []
        
        # Tokenize query for matching
        query_tokens = set(query.lower().split())
        results = []
        
        for mid, m in data.items():
            # Apply metadata filter
            if filter_metadata:
                match = True
                for k, v in filter_metadata.items():
                    if m.get("metadata", {}).get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            
            # Calculate relevance score based on token overlap
            content = m.get("content", "").lower()
            task = m.get("metadata", {}).get("task", "").lower()
            combined_text = f"{content} {task}"
            
            # Count matching tokens
            text_tokens = set(combined_text.split())
            overlap = len(query_tokens & text_tokens)
            
            if overlap > 0:
                score = overlap / len(query_tokens)
                results.append(MemoryEntry(
                    id=mid,
                    content=m.get("content", ""),
                    metadata=m.get("metadata", {}),
                    score=score,
                ))
        
        # Sort by score and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def get_all(
        self,
        limit: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntry]:
        """
        Get all memories matching filter.
        """
        self._ensure_initialized()
        
        # Try ChromaDB first - only if it has data
        if self._collection:
            try:
                count = self._collection.count()
                if count > 0:
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
                                score=1.0,
                            ))
                        return entries
            except Exception:
                pass  # Fall through to JSON fallback
        
        # JSON fallback
        return self._get_all_from_json(limit, filter_metadata)
    
    def get_recent(self, limit: int = 5, node: str = "general") -> List[MemoryEntry]:
        """
        Get most recent memories sorted by timestamp.
        Useful for loading conversation context.
        """
        # Always use JSON file for chronological history (it preserves order/completeness)
        candidates = self._get_all_from_json(limit=limit * 10)
        
        # Filter by Node
        node = node.lower().strip()
        candidates = [
            c for c in candidates 
            if c.metadata.get("node", "general") == node
        ]
        
        # Sort by timestamp in metadata (descending)
        candidates.sort(
            key=lambda x: x.metadata.get("timestamp", ""), 
            reverse=True
        )
        
        return candidates[:limit]
    
    def _get_all_from_json(
        self,
        limit: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[MemoryEntry]:
        """Get all memories from JSON fallback storage."""
        import json
        
        memories_file = self.persist_dir / "memories.json"
        if not memories_file.exists():
            return []
        
        try:
            data = json.loads(memories_file.read_text())
        except Exception:
            return []
        
        all_memories = []
        for mid, m in data.items():
            # Apply metadata filter
            if filter_metadata:
                match = True
                for k, v in filter_metadata.items():
                    if m.get("metadata", {}).get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            
            all_memories.append(MemoryEntry(
                id=mid,
                content=m.get("content", ""),
                metadata=m.get("metadata", {}),
                score=1.0
            ))
        
        return all_memories[:limit] if limit else all_memories
    def get_persona(self) -> str:
        """Get consolidated user persona from memory."""
        memories = self.search("user persona details", limit=5, filter_metadata={"type": "persona"})
        if not memories:
            return ""
        
        return "\n".join([f"- {m.content}" for m in memories])

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        self._ensure_initialized()
        
        chroma_success = False
        if self._collection:
            try:
                self._collection.delete(ids=[memory_id])
                chroma_success = True
            except Exception:
                pass 
        
        # Always update JSON Source of Truth
        json_success = self._delete_from_json(memory_id)
        
        return chroma_success or json_success
    
    def _delete_from_json(self, memory_id: str) -> bool:
        """Delete from JSON fallback storage."""
        import json
        
        memories_file = self.persist_dir / "memories.json"
        if not memories_file.exists():
            return False
        
        try:
            data = json.loads(memories_file.read_text())
            if memory_id in data:
                del data[memory_id]
                memories_file.write_text(json.dumps(data, indent=2))
                return True
            return False
        except Exception:
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

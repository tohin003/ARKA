
import sys
import os
import json
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from arka.memory.memory_client import MemoryClient

def test_memory_nodes_json_only():
    print("🧠 Starting Memory Nodes Architecture Test (JSON Logic Only)...")
    
    test_dir = Path.home() / ".arka" / "test_memory_json"
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize client but MOCK the ChromaDB part to prevent download
    client = MemoryClient(persist_dir=str(test_dir))
    # Force mock collection so it doesn't try to load real chroma
    client._collection = MagicMock()
    client._initialized = True # Skip initialization logic
    
    # 1. Test Node Creation
    print("\n[1] Testing Node Creation...")
    print(client.create_node("beta_project"))
    nodes = client.list_nodes()
    print(f"Nodes: {nodes}")
    assert "beta_project" in nodes
    assert "general" in nodes
    print("✅ Node creation passed.")
    
    # 2. Test Dual Write & Linking
    print("\n[2] Testing Dual Write & Linking...")
    msg = "The secret code is 999."
    # Store in beta_project
    primary_id = client.add(msg, node="beta_project")
    print(f"Stored in 'beta_project' with ID: {primary_id}")
    
    # Verify contents directly from JSON
    memories = client._get_all_from_json(limit=100)
    
    # Find primary
    primary = next((m for m in memories if m.id == primary_id), None)
    assert primary is not None
    assert primary.metadata["node"] == "beta_project"
    print("✅ Primary entry found in 'beta_project'.")
    
    # Find general copy
    general_copy = next((m for m in memories if m.metadata.get("node") == "general" and m.content == msg), None)
    assert general_copy is not None
    assert general_copy.id != primary_id # IDs must differ
    
    # CHECK POINTERS
    print(f"General Copy Metadata: {general_copy.metadata}")
    assert general_copy.metadata.get("ref_node") == "beta_project"
    assert general_copy.metadata.get("ref_id") == primary_id
    assert general_copy.metadata.get("is_ref") is True
    print("✅ Linked Reference verified (General -> Beta Pointer is valid).")
    
    # 3. Test Search (Time Aware / Sliding Window)
    # Search uses _get_all_from_json, so it works even without Chroma
    print("\n[3] Testing Context Search...")
    
    results_beta = client.search_time_aware("secret code", node="beta_project")
    print(f"Search 'beta_project' results: {[r.content for r in results_beta]}")
    assert len(results_beta) > 0
    assert results_beta[0].content == msg
    
    results_gen = client.search_time_aware("secret code", node="general")
    print(f"Search 'general' results: {[r.content for r in results_gen]}")
    assert len(results_gen) > 0
    
    print(client.create_node("gamma_project"))
    results_gamma = client.search_time_aware("secret code", node="gamma_project")
    assert len(results_gamma) == 0
    print("✅ Search Filtering passed.")
    
    # 4. Test Deletion
    print("\n[4] Testing Node Deletion...")
    print(client.delete_node("beta_project"))
    
    nodes_after = client.list_nodes()
    assert "beta_project" not in nodes_after
    
    remaining = client._get_all_from_json(limit=100)
    beta_left = [m for m in remaining if m.metadata.get("node") == "beta_project"]
    assert len(beta_left) == 0
    print("✅ Node memories deleted.")
    
    # Persisted copy
    gen_left = [m for m in remaining if m.metadata.get("ref_node") == "beta_project"]
    assert len(gen_left) == 1
    print("✅ General node copy preserved.")
    
    print("\n🎉 ALL LOGIC TESTS PASSED.")

if __name__ == "__main__":
    test_memory_nodes_json_only()

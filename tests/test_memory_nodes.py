
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from arka.memory.memory_client import MemoryClient

def test_memory_nodes():
    print("🧠 Starting Memory Nodes Architecture Test...")
    
    # Use a specific test directory to avoid messing with real user memory
    test_dir = Path.home() / ".arka" / "test_memory"
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    client = MemoryClient(persist_dir=str(test_dir))
    
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
    print("\n[3] Testing Context Search...")
    # Search in specific node
    results_beta = client.search_time_aware("secret code", node="beta_project")
    print(f"Search 'beta_project': Found {len(results_beta)} items.")
    assert len(results_beta) > 0
    assert results_beta[0].content == msg
    
    # Search in general node
    results_gen = client.search_time_aware("secret code", node="general")
    print(f"Search 'general': Found {len(results_gen)} items.")
    assert len(results_gen) > 0
    
    # Search in wrong node (should fail)
    print(client.create_node("gamma_project"))
    results_gamma = client.search_time_aware("secret code", node="gamma_project")
    print(f"Search 'gamma_project': Found {len(results_gamma)} items.")
    assert len(results_gamma) == 0
    print("✅ Search Filtering passed.")
    
    # 4. Test Deletion
    print("\n[4] Testing Node Deletion...")
    print(client.delete_node("beta_project"))
    
    nodes_after = client.list_nodes()
    assert "beta_project" not in nodes_after
    
    # Verify memories deleted
    # Note: Logic deletes memories where node='beta_project'.
    # Does it delete the 'general' copy? NO. The linked reference persists in General (Historical record).
    # This is usually desired (don't lose history just because folder deleted), 
    # OR user might want cascading delete. The current logic deletes only the 'beta_project' entries.
    
    remaining = client._get_all_from_json(limit=100)
    beta_left = [m for m in remaining if m.metadata.get("node") == "beta_project"]
    assert len(beta_left) == 0
    print("✅ Node memories deleted.")
    
    # Verify General copy still exists (Historical Persistence)
    gen_left = [m for m in remaining if m.metadata.get("ref_node") == "beta_project"]
    print(f"General copies remaining: {len(gen_left)}")
    assert len(gen_left) == 1
    print("✅ General node copy preserved (Safe!).")
    
    print("\n🎉 ALL TESTS PASSED. Data Structure Integrity Verified.")

if __name__ == "__main__":
    test_memory_nodes()

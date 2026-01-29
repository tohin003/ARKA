from typing import Dict, Any, List
from arka.memory import get_memory

def create_memory_node(name: str) -> str:
    """
    Create a new specialized memory node.
    Use this when the user asks to start a new 'category' or 'project' for memory.
    
    Args:
        name: The name of the node (e.g. "project_alpha", "learning_python")
    """
    client = get_memory()
    return client.create_node(name)

def list_memory_nodes() -> str:
    """
    List all available memory nodes.
    Use this to see where data can be stored.
    """
    client = get_memory()
    nodes = client.list_nodes()
    return "Available Memory Nodes:\n" + "\n".join([f"- {n}" for n in nodes])

def store_memory(content: str, node: str = "general") -> str:
    """
    Store specific information into memory.
    
    Args:
        content: The fact or data to remember.
        node: The target node (default: "general"). 
              If specific node is used, it AUTOMATICALLY also saves to 'general'.
    """
    client = get_memory()
    try:
        # Check if node exists, if not, warn (but creating on fly is also fine via add logic?)
        # Actually client.add doesn't enforce existence, but let's enforce explicitly for clarity
        existing = client.list_nodes()
        node_clean = node.lower().strip()
        if node_clean not in existing:
             # Auto-create? Or error? User said "create node" is an action.
             # Let's auto-create for smoother UX if explicit tool use
             client.create_node(node_clean)
        
        mid = client.add(content, metadata={"type": "manual_entry"}, node=node_clean)
        return f"Stored in node '{node_clean}' (ID: {mid})"
    except Exception as e:
        return f"Failed to store memory: {e}"

def delete_memory_node(name: str) -> str:
    """
    Delete a memory node and all its data.
    
    Args:
        name: Name of node to delete. Cannot be 'general'.
    """
    client = get_memory()
    return client.delete_node(name)

# Tool Definitions for tool_executor
MEMORY_TOOLS = {
    "create_memory_node": create_memory_node,
    "list_memory_nodes": list_memory_nodes,
    "store_memory": store_memory,
    "delete_memory_node": delete_memory_node
}

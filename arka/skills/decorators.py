"""
Decorators for ARKA Skills.
Use @arka_tool to register a function as a tool.
"""

from typing import Dict, Any, Optional
import functools

def arka_tool(name: str, description: str, parameters: Dict[str, Any]):
    """
    Decorator to mark a function as an ARKA tool.
    
    Args:
        name: The tool name (e.g., 'pdf_merge')
        description: Description for the LLM
        parameters: JSON schema parameters
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Attach metadata for registry scanner
        wrapper._is_arka_tool = True
        wrapper._tool_name = name
        wrapper._tool_description = description
        wrapper._tool_parameters = parameters
        return wrapper
    return decorator

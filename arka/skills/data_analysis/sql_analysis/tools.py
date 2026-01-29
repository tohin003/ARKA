from arka.skills.decorators import arka_tool
from typing import Dict, Any
import re

try:
    from sqlalchemy import create_engine, text
except ImportError:
    pass

@arka_tool(
    name="execute_readonly_sql",
    description="Execute a SAFE read-only SQL query.",
    parameters={
        "type": "object",
        "properties": {
            "connection_string": {"type": "string", "description": "Database URL (SQLAlchemy format)"},
            "query": {"type": "string", "description": "SQL Query (SELECT only)"}
        },
        "required": ["connection_string", "query"]
    }
)
def execute_readonly_sql(connection_string: str, query: str) -> str:
    """
    Executes a SQL query with safety checks.
    """
    # 1. Safety Check
    destructive_patterns = [
        r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", 
        r"\bALTER\b", r"\bTRUNCATE\b", r"\bCREATE\b", r"\bGRANT\b"
    ]
    query_upper = query.upper()
    for pattern in destructive_patterns:
        if re.search(pattern, query_upper):
            raise ValueError(f"Security Alert: Query contains potentially destructive keyword '{pattern}'. Action Blocked.")
            
    try:
        engine = create_engine(connection_string)
        with engine.connect() as connection:
            result = connection.execute(text(query))
            keys = result.keys()
            rows = result.fetchall()
            
            # Format as simple text table
            output = [f"| {' | '.join(keys)} |", f"| {'---'*len(keys)} |"]
            for row in rows[:50]: # Limit to 50 rows
                output.append(f"| {' | '.join(str(x) for x in row)} |")
                
            if len(rows) > 50:
                output.append(f"... ({len(rows)-50} more rows truncated)")
                
            return "\n".join(output)
            
    except Exception as e:
        return f"SQL Error: {str(e)}"

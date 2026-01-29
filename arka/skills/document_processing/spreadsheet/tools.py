from arka.skills.decorators import arka_tool
import pandas as pd
import os

@arka_tool(
    name="read_spreadsheet",
    description="Read an Excel or CSV file and return a text preview.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to xlsx or csv file"},
            "rows": {"type": "integer", "description": "Number of rows to preview (default 20)"}
        },
        "required": ["path"]
    }
)
def read_spreadsheet(path: str, rows: int = 20) -> str:
    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path, nrows=rows)
        else:
            df = pd.read_excel(path, nrows=rows)
            
        return df.to_markdown(index=False)
    except Exception as e:
        return f"Error reading spreadsheet: {e}"

@arka_tool(
    name="get_spreadsheet_info",
    description="Get info (columns, shape) about a spreadsheet.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to file"}
        },
        "required": ["path"]
    }
)
def get_spreadsheet_info(path: str) -> str:
    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path, nrows=5)
        else:
            df = pd.read_excel(path, nrows=5)
            
        info = f"""
File: {os.path.basename(path)}
Columns: {', '.join(df.columns)}
Preview Shape: {df.shape} (loaded partial)
dtypes:
{df.dtypes}
"""
        return info
    except Exception as e:
        return f"Error: {e}"

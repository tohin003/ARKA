from arka.skills.decorators import arka_tool
import pypdf
import os
from typing import List

@arka_tool(
    name="pdf_page_count",
    description="Get the number of pages in a PDF.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to PDF file"}
        },
        "required": ["path"]
    }
)
def pdf_page_count(path: str) -> str:
    try:
        reader = pypdf.PdfReader(path)
        return str(len(reader.pages))
    except Exception as e:
        return f"Error: {e}"

@arka_tool(
    name="pdf_extract_text",
    description="Extract text from a PDF.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to PDF file"},
            "page_start": {"type": "integer", "description": "Start page (0-indexed)"},
            "page_end": {"type": "integer", "description": "End page (optional)"}
        },
        "required": ["path"]
    }
)
def pdf_extract_text(path: str, page_start: int = 0, page_end: int = None) -> str:
    try:
        reader = pypdf.PdfReader(path)
        text = []
        end = page_end if page_end is not None else len(reader.pages)
        
        for i in range(page_start, min(end, len(reader.pages))):
            text.append(f"--- Page {i+1} ---")
            text.append(reader.pages[i].extract_text() or "[No Text]")
            
        return "\n".join(text)
    except Exception as e:
        return f"Error: {e}"

@arka_tool(
    name="pdf_merge",
    description="Merge multiple PDFs into one.",
    parameters={
        "type": "object",
        "properties": {
            "paths": {"type": "array", "items": {"type": "string"}, "description": "List of input PDF paths"},
            "output_path": {"type": "string", "description": "Path for the merged PDF"}
        },
        "required": ["paths", "output_path"]
    }
)
def pdf_merge(paths: List[str], output_path: str) -> str:
    try:
        merger = pypdf.PdfWriter()
        for p in paths:
            merger.append(p)
        merger.write(output_path)
        merger.close()
        return f"Successfully merged {len(paths)} files to {output_path}"
    except Exception as e:
        return f"Error: {e}"

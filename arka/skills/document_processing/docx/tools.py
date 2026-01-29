from arka.skills.decorators import arka_tool
from docx import Document
import os

@arka_tool(
    name="read_docx",
    description="Read text content from a Word (.docx) file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to docx file"}
        },
        "required": ["path"]
    }
)
def read_docx(path: str) -> str:
    try:
        doc = Document(path)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        return f"Error: {e}"

@arka_tool(
    name="create_docx",
    description="Create a new Word document with text content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Output path"},
            "content": {"type": "string", "description": "Text content"},
            "heading": {"type": "string", "description": "Optional heading"}
        },
        "required": ["path", "content"]
    }
)
def create_docx(path: str, content: str, heading: str = None) -> str:
    try:
        doc = Document()
        if heading:
            doc.add_heading(heading, 0)
        doc.add_paragraph(content)
        doc.save(path)
        return f"Document saved to {path}"
    except Exception as e:
        return f"Error: {e}"

from arka.skills.decorators import arka_tool
from pptx import Presentation
import os

@arka_tool(
    name="create_presentation",
    description="Create a PowerPoint presentation from title and slides.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Output path (.pptx)"},
            "title": {"type": "string", "description": "Presentation title"},
            "slides": {
                "type": "array", 
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"}
                    }
                },
                "description": "List of slides (title + content)"
            }
        },
        "required": ["path", "title", "slides"]
    }
)
def create_presentation(path: str, title: str, slides: list) -> str:
    try:
        prs = Presentation()
        # Title Slide
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        slide.shapes.title.text = title
        
        # Content Slides
        bullet_layout = prs.slide_layouts[1]
        for s_data in slides:
            slide = prs.slides.add_slide(bullet_layout)
            slide.shapes.title.text = s_data.get("title", "Untitled")
            tf = slide.placeholders[1].text_frame
            tf.text = s_data.get("content", "")
            
        prs.save(path)
        return f"Saved presentation to {path}"
    except Exception as e:
        return f"Error creating PPTX: {e}"

@arka_tool(
    name="read_presentation",
    description="Read text from a PPTX file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to PPTX file"}
        },
        "required": ["path"]
    }
)
def read_presentation(path: str) -> str:
    try:
        prs = Presentation(path)
        text = []
        for i, slide in enumerate(prs.slides):
            text.append(f"--- Slide {i+1} ---")
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    except Exception as e:
        return f"Error reading PPTX: {e}"

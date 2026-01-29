
from arka.skills.decorators import arka_tool
from googlesearch import search
import requests

@arka_tool(
    name="find_company_info",
    description="Find info about a company.",
    parameters={
        "type": "object",
        "properties": {
            "company": {"type": "string"}
        },
        "required": ["company"]
    }
)
def find_company_info(company: str) -> str:
    try:
        results = list(search(f"{company} official site contact", num_results=3))
        return f"Found URLs: {results}"
    except Exception as e:
        return f"Error: {e}"


from arka.skills.decorators import arka_tool
import requests
from bs4 import BeautifulSoup

@arka_tool(
    name="extract_article_text",
    description="Extract main text from a web article.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "required": ["url"]
    }
)
def extract_article_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        # Simple extraction of p tags
        text = "\n".join([p.text for p in soup.find_all('p')])
        return text[:5000] # Limit
    except Exception as e:
        return f"Error: {e}"

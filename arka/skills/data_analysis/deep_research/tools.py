from arka.skills.decorators import arka_tool
from typing import Dict, Any, List
try:
    from googlesearch import search
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    pass

@arka_tool(
    name="perform_deep_research",
    description="Search Google and extract content from top results.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search topic"},
            "max_depth": {"type": "integer", "description": "Number of pages to visit (default 3)"}
        },
        "required": ["query"]
    }
)
def perform_deep_research(query: str, max_depth: int = 3) -> str:
    """
    Performs deep research by searching and scraping top results.
    """
    report = [f"Research Report: {query}\n{'='*30}\n"]
    
    try:
        # 1. Search
        report.append(f"Searching for: '{query}'...")
        urls = list(search(query, num_results=max_depth, advanced=True))
        
        # 2. Visit
        for i, result in enumerate(urls[:max_depth], 1):
            url = result.url
            title = result.title
            report.append(f"\nSource {i}: {title}\nURL: {url}")
            
            try:
                # Simple Request (Fast)
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                resp = requests.get(url, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Extract paragraphs
                    paras = soup.find_all('p')
                    text_content = ' '.join([p.get_text() for p in paras])
                    
                    # Truncate
                    preview = text_content[:2000] + "..." if len(text_content) > 2000 else text_content
                    report.append(f"Content Preview:\n{preview}\n{'-'*20}")
                else:
                    report.append(f"Failed to load: Status {resp.status_code}")
            except Exception as e:
                report.append(f"Error reading page: {e}")
                
    except Exception as e:
        return f"Research failed: {e}"
        
    return "\n".join(report)

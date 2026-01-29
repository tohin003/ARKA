"""
ARKA Browser Tool
Web browsing using Browser-Use and Playwright.
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from arka.tools.base_tool import BaseTool, ToolResult, ToolCategory


@dataclass
class PageContent:
    """Extracted page content."""
    title: str
    url: str
    text: str
    links: List[Dict[str, str]]


class BrowserTool(BaseTool):
    """
    Web browsing with Browser-Use integration.
    Falls back to simple HTTP for basic operations.
    """
    
    NAME = "browser"
    DESCRIPTION = "Browse the web, interact with pages via DOM IDs, and extract content"
    CATEGORY = ToolCategory.WEB
    REQUIRES_CONFIRMATION = False
    
    def __init__(self, headless: bool = False):
        super().__init__()
        from arka.core.browser_manager import get_browser_manager
        self._manager = get_browser_manager()
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "type", "screenshot", "get_text", "search", "get_dom", "get_interactive", "connect"],
                    "description": "Browser action to perform",
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector or Arka ID (integer)",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type, search query, or Port number for connect",
                },
            },
            "required": ["action"],
        }
    
    def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a browser action using persistent BrowserManager.
        """
        try:
            if action == "connect":
                port = int(text) if text and text.isdigit() else 9222
                success = self._manager.connect_external(port)
                if success:
                    return ToolResult(True, f"Successfully connected to external Chrome on port {port}. DOM features now active on your browser.")
                else:
                    return ToolResult(False, "", "Failed to connect. Ensure Chrome is running with '--remote-debugging-port=9222'")

            if action == "search":
                return self._search(text or "")
            
            # Browser Manager Actions
            if action == "navigate" and url:
                self._manager.navigate(url)
                title = self._manager.get_title()
                return ToolResult(True, f"Navigated to: {title}", metadata={"url": url})
            
            elif action in ["get_dom", "get_interactive"]:
                dom_tree = self._manager.get_dom_snapshot()
                return ToolResult(True, f"Interactive Elements:\n{dom_tree}")
                
            elif action == "click" and selector:
                self._manager.click(selector)
                return ToolResult(True, f"Clicked: {selector}")
            
            elif action == "type" and selector and text:
                self._manager.type_text(selector, text)
                return ToolResult(True, f"Typed into: {selector}")
            
            elif action == "screenshot":
                b64 = self._manager.screenshot()
                return ToolResult(True, "Screenshot captured", metadata={"screenshot": b64})
            
            elif action == "get_text":
                txt = self._manager.get_visible_text()
                return ToolResult(True, txt[:5000])
                
            return ToolResult(False, "", f"Invalid or missing params for action: {action}")
            
        except Exception as e:
            return ToolResult(False, "", str(e))

    # Async stubs removed as we use Sync Playwright via Manager
    async def _execute_async(self, *args, **kwargs):
        raise NotImplementedError("Use sync execute() with BrowserManager")
    
    async def _simple_fetch(self, url: str) -> ToolResult:
        """Simple HTTP fetch without full browser."""
        try:
            import httpx
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, timeout=30)
                
                # Try to extract text
                content = response.text
                
                # Basic HTML to text
                if "<html" in content.lower():
                    # Simple extraction
                    import re
                    # Remove scripts and styles
                    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
                    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
                    # Remove tags
                    content = re.sub(r'<[^>]+>', ' ', content)
                    # Clean whitespace
                    content = ' '.join(content.split())
                
                return ToolResult(
                    success=True,
                    output=content[:5000],
                    metadata={"url": url, "status": response.status_code},
                )
                
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    async def _search(self, query: str) -> ToolResult:
        """Perform a web search."""
        # Use DuckDuckGo HTML (no API key needed)
        try:
            import httpx
            
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, timeout=30)
                
                # Extract results (simplified)
                import re
                results = []
                
                # Find result links
                for match in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*class="result__a"[^>]*>([^<]+)</a>', response.text):
                    url = match.group(1)
                    title = match.group(2)
                    results.append(f"- {title}: {url}")
                
                if results:
                    return ToolResult(
                        success=True,
                        output=f"Search results for '{query}':\n\n" + "\n".join(results[:10]),
                        metadata={"query": query, "count": len(results)},
                    )
                else:
                    return ToolResult(True, f"No results found for: {query}")
                    
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    def navigate(self, url: str) -> str:
        """Navigate to a URL and get content."""
        result = self.execute("navigate", url=url)
        if result.success:
            return result.output
        raise RuntimeError(result.error)
    
    def search(self, query: str) -> str:
        """Perform a web search."""
        result = self.execute("search", text=query)
        if result.success:
            return result.output
        raise RuntimeError(result.error)

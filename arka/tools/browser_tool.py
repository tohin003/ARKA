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
    DESCRIPTION = "Browse the web, interact with pages, and extract content"
    CATEGORY = ToolCategory.WEB
    REQUIRES_CONFIRMATION = False
    
    def __init__(self, headless: bool = True):
        super().__init__()
        self.headless = headless
        self._browser = None
        self._playwright = None
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "type", "screenshot", "get_text", "search"],
                    "description": "Browser action to perform",
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for element interactions",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type or search query",
                },
            },
            "required": ["action"],
        }
    
    async def _ensure_browser(self):
        """Initialize browser if needed."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless
                )
            except ImportError:
                raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")
    
    async def _close_browser(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a browser action.
        
        Args:
            action: navigate, click, type, screenshot, get_text, search
            url: URL for navigation
            selector: CSS selector for interactions
            text: Text to type or search query
            
        Returns:
            ToolResult with page content or action result
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._execute_async(action, url, selector, text)
        )
    
    async def _execute_async(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
    ) -> ToolResult:
        """Async browser execution."""
        
        if action == "search":
            return await self._search(text or "")
        
        if action == "navigate" and url:
            # Try simple HTTP first for just getting content
            return await self._simple_fetch(url)
        
        # Full browser for interactive actions
        try:
            await self._ensure_browser()
            
            page = await self._browser.new_page()
            
            try:
                if action == "navigate" and url:
                    await page.goto(url, wait_until="networkidle")
                    title = await page.title()
                    content = await page.content()
                    return ToolResult(
                        success=True,
                        output=f"Navigated to: {title}\n\n{content[:5000]}",
                        metadata={"url": url, "title": title},
                    )
                
                elif action == "click" and selector:
                    await page.click(selector)
                    return ToolResult(True, f"Clicked: {selector}")
                
                elif action == "type" and selector and text:
                    await page.fill(selector, text)
                    return ToolResult(True, f"Typed into: {selector}")
                
                elif action == "screenshot":
                    screenshot = await page.screenshot()
                    return ToolResult(
                        True,
                        "Screenshot captured",
                        metadata={"screenshot": screenshot},
                    )
                
                elif action == "get_text":
                    text_content = await page.inner_text("body")
                    return ToolResult(True, text_content[:5000])
                
                else:
                    return ToolResult(False, "", f"Invalid action or missing params: {action}")
                    
            finally:
                await page.close()
                
        except Exception as e:
            return ToolResult(False, "", str(e))
    
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

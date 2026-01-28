"""
ARKA Browser Manager
Manages Playwright instance for robust web automation.
"""

import time
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

class BrowserManager:
    """
    Manages a Chrome browser instance via Playwright.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._is_active = False

    def start(self):
        """Start the browser."""
        if self._is_active:
            return

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            channel="chrome",  # Use installed Chrome if available
            args=["--no-first-run", "--no-default-browser-check"]
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800}
        )
        self.page = self.context.new_page()
        self._is_active = True

    def stop(self):
        """Stop the browser."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self._is_active = False

    def navigate(self, url: str):
        """Go to a URL."""
        if not self._is_active:
            self.start()
        
        # Ensure scheme
        if not url.startswith("http"):
            url = "https://" + url
            
        self.page.goto(url, wait_until="domcontentloaded")

    def click(self, selector: str):
        """Click an element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        self.page.click(selector, timeout=5000)

    def type_text(self, selector: str, text: str):
        """Type text into an element."""
        if not self.page:
            raise RuntimeError("Browser not started")
        self.page.fill(selector, text, timeout=5000)

    def press_key(self, key: str):
        """Press a keyboard key."""
        if not self.page:
            raise RuntimeError("Browser not started")
        self.page.keyboard.press(key)

    def get_title(self) -> str:
        """Get page title."""
        return self.page.title() if self.page else ""

    def get_visible_text(self) -> str:
        """Get visible text simplified."""
        if not self.page:
            return ""
        return self.page.evaluate("document.body.innerText")

    def get_dom_snapshot(self) -> str:
        """Get simplified DOM for LLM analysis."""
        # Simple extraction of interactive elements
        # This script returns a JSON-like structure of simplified nodes
        # For now, just returning HTML might be too large. 
        # Ideally, we inject a script to find interactables.
        
        script = """
        () => {
            const elements = document.querySelectorAll('button, a, input, [role="button"]');
            const data = [];
            elements.forEach((el, index) => {
                if (el.offsetParent === null) return; // Hidden
                
                let label = el.innerText || el.getAttribute('aria-label') || el.value || "";
                label = label.slice(0, 50).replace(/\\n/g, " ").trim();
                
                // Construct a robust selector
                let selector = el.tagName.toLowerCase();
                if (el.id) selector += `#${el.id}`;
                else if (el.className) selector += `.${el.className.split(" ")[0]}`;
                
                data.push(`[${index}] <${el.tagName.toLowerCase()}> "${label}"`);
            });
            return data.join("\\n");
        }
        """
        if not self.page:
            return ""
        try:
            return self.page.evaluate(script)
        except Exception as e:
            return f"Error extracting DOM: {e}"

    def screenshot(self) -> str:
        """Return base64 screenshot."""
        if not self.page:
            return ""
        import base64
        bytes_data = self.page.screenshot()
        return base64.b64encode(bytes_data).decode('utf-8')


# Global instance
_browser_manager = None

def get_browser_manager() -> BrowserManager:
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(headless=False)
    return _browser_manager

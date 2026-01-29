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

    def connect_external(self, port: int = 9222) -> bool:
        """Connect to an existing external Chrome instance via CDP."""
        if self._is_active:
            self.stop()
        
        # First try native CDP (more reliable)
        if self._connect_cdp_native(port):
            return True
            
        # Fallback to Playwright
        self.playwright = sync_playwright().start()
        try:
            # Connect to existing browser
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://localhost:{port}")
            self.context = self.browser.contexts[0]
            
            # Use the active tab or create new
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = self.context.new_page()
                
            self._is_active = True
            return True
        except Exception as e:
            print(f"Failed to connect to CDP: {e}")
            if self.playwright:
                self.playwright.stop()
            return False
    
    def _connect_cdp_native(self, port: int) -> bool:
        """Connect using native WebSocket CDP (bypasses Playwright issues)."""
        import requests
        import websocket
        import json
        
        try:
            # Get page list
            resp = requests.get(f"http://localhost:{port}/json/list", timeout=2)
            pages = resp.json()
            
            # Find first page
            target = next((p for p in pages if p['type'] == 'page'), None)
            if not target:
                return False
            
            self._cdp_ws_url = target['webSocketDebuggerUrl']
            self._cdp_port = port
            self._is_active = True
            self._use_native_cdp = True
            return True
            
        except Exception as e:
            print(f"Native CDP connection failed: {e}")
            return False
    
    def evaluate_cdp(self, js_expression: str) -> Any:
        """Evaluate JavaScript via native CDP WebSocket."""
        import websocket
        import json
        
        if not hasattr(self, '_cdp_ws_url') or not self._cdp_ws_url:
            raise RuntimeError("No native CDP connection")
        
        ws = websocket.create_connection(self._cdp_ws_url)
        try:
            msg = {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_expression,
                    "returnByValue": True
                }
            }
            ws.send(json.dumps(msg))
            result = json.loads(ws.recv())
            
            if 'result' in result and 'result' in result['result']:
                return result['result']['result'].get('value')
            return None
        finally:
            ws.close()

    def stop(self):
        """Stop the browser."""
        # Check if connected via CDP, simple close might not be enough context
        if self.context:
            try:
                self.context.close()
            except: pass
        if self.browser:
            try:
                self.browser.close()
            except: pass
        if self.playwright:
            try:
                self.playwright.stop()
            except: pass
        self._is_active = False

    def navigate(self, url: str):
        """Go to a URL."""
        # Ensure scheme if missing
        if not any(url.startswith(p) for p in ["http", "https", "file:", "data:", "chrome:", "about:"]):
            url = "https://" + url
        
        # Use native CDP if available
        if hasattr(self, '_use_native_cdp') and self._use_native_cdp:
            self.evaluate_cdp(f"window.location.href = '{url}'")
            return
            
        # Fallback to Playwright
        if not self._is_active:
            self.start()
            
        self.page.goto(url, wait_until="domcontentloaded")

    def click(self, selector: str):
        """Click an element. Supports ID (e.g. '12') or CSS selector."""
        # Use native CDP if available
        if hasattr(self, '_use_native_cdp') and self._use_native_cdp:
            if selector.isdigit():
                js = f"document.querySelector('[data-arka-id=\"{selector}\"]')?.click()"
            else:
                js = f"document.querySelector('{selector}')?.click()"
            self.evaluate_cdp(js)
            return
            
        # Fallback to Playwright
        if not self.page:
            raise RuntimeError("Browser not started")
            
        # If numeric, assume it's our Arka ID
        if selector.isdigit():
            selector = f"[data-arka-id='{selector}']"
            
        self.page.click(selector, timeout=5000)

    def type_text(self, selector: str, text: str):
        """Type text into an element."""
        # Use native CDP if available
        if hasattr(self, '_use_native_cdp') and self._use_native_cdp:
            if selector.isdigit():
                js = f'''
                    (function() {{
                        const el = document.querySelector('[data-arka-id="{selector}"]');
                        if (el) {{
                            el.focus();
                            el.value = "{text}";
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }})()
                '''
            else:
                js = f'''
                    (function() {{
                        const el = document.querySelector('{selector}');
                        if (el) {{
                            el.focus();
                            el.value = "{text}";
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                    }})()
                '''
            self.evaluate_cdp(js)
            return
            
        # Fallback to Playwright
        if not self.page:
            raise RuntimeError("Browser not started")
            
        if selector.isdigit():
            selector = f"[data-arka-id='{selector}']"
            
        self.page.fill(selector, text, timeout=5000)

    def select_option(self, selector: str, value: str):
        """Select an option in a dropdown by value or visible text."""
        # Use native CDP if available
        if hasattr(self, '_use_native_cdp') and self._use_native_cdp:
            if selector.isdigit():
                sel = f'[data-arka-id="{selector}"]'
            else:
                sel = selector
            
            # JavaScript to select option by text or value
            js = f'''
                (function() {{
                    const select = document.querySelector('{sel}');
                    if (!select) return 'Element not found';
                    
                    const options = select.options;
                    const searchValue = "{value}".toLowerCase();
                    
                    for (let i = 0; i < options.length; i++) {{
                        const optText = options[i].text.toLowerCase();
                        const optVal = options[i].value.toLowerCase();
                        
                        if (optText.includes(searchValue) || optVal.includes(searchValue) || 
                            searchValue.includes(optText) || searchValue.includes(optVal)) {{
                            select.selectedIndex = i;
                            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return 'Selected: ' + options[i].text;
                        }}
                    }}
                    return 'Option not found: ' + searchValue;
                }})()
            '''
            return self.evaluate_cdp(js)
            
        # Fallback to Playwright
        if not self.page:
            raise RuntimeError("Browser not started")
            
        if selector.isdigit():
            selector = f"[data-arka-id='{selector}']"
            
        self.page.select_option(selector, label=value, timeout=5000)

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
        """Get simplified DOM with actionable IDs."""
        # JS Script to label elements and extract tree
        script = """
        (() => {
            let items = [];
            // Expanded selectors to catch LinkedIn/SPA elements
            const candidates = document.querySelectorAll('button, a, input, textarea, select, [role="button"], [role="link"], [role="menuitem"], [onclick]');
            
            candidates.forEach((el, index) => {
                // Skip hidden
                if (el.offsetParent === null) return;
                
                // Assign ID if missing (or overwrite for consistency)
                el.setAttribute('data-arka-id', index);
                
                let tagName = el.tagName.toLowerCase();
                let type = el.getAttribute('type') || '';
                
                // For form fields, try to find associated label
                let label = "";
                if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
                    // Method 1: Check for label with 'for' attribute
                    const elId = el.id;
                    if (elId) {
                        const labelEl = document.querySelector(`label[for="${elId}"]`);
                        if (labelEl) label = labelEl.innerText;
                    }
                    // Method 2: Check parent for label-like text
                    if (!label) {
                        const parent = el.closest('.form-group, .field, .input-wrapper, div');
                        if (parent) {
                            const parentLabel = parent.querySelector('label, .label, span');
                            if (parentLabel) label = parentLabel.innerText;
                        }
                    }
                    // Method 3: Use placeholder or aria-label
                    if (!label) {
                        label = el.placeholder || el.getAttribute('aria-label') || el.getAttribute('name') || "";
                    }
                    // Include current value if it's a filled input
                    const currentVal = el.value;
                    if (currentVal && currentVal.length > 0) {
                        label += ` [current: ${currentVal.substring(0, 30)}]`;
                    }
                } else {
                    // For buttons/links, use innerText
                    label = el.innerText || 
                            el.getAttribute('aria-label') || 
                            el.title || 
                            el.getAttribute('data-control-name') || 
                            "";
                }
                            
                label = label.replace(/\\n/g, " ").replace(/\\s+/g, " ").trim().substring(0, 120);
                
                // Only include if specific enough or clearly interactive
                if (label.length > 0 || tagName === 'input' || tagName === 'select' || tagName === 'textarea') {
                    items.push(`[${index}] <${tagName} ${type}> "${label}"`);
                }
            });
            return items.join("\\n");
        })()
        """
        
        try:
            # Use native CDP if available
            if hasattr(self, '_use_native_cdp') and self._use_native_cdp:
                return self.evaluate_cdp(script) or ""
            
            # Fallback to Playwright
            if not self.page:
                return "Error: Browser not started"
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

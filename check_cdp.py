
from playwright.sync_api import sync_playwright

def check_connection():
    try:
        with sync_playwright() as p:
            print("Creating CDP connection...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            print("✅ Success! Connected to Comet via CDP.")
            print(f"Contexts: {len(browser.contexts)}")
            browser.close()
            return True
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return False

if __name__ == "__main__":
    check_connection()

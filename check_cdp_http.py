
import urllib.request
import json

try:
    with urllib.request.urlopen("http://localhost:9222/json/version", timeout=2) as response:
        data = json.load(response)
        print("✅ CDP Endpoint Active!")
        print(f"Browser: {data.get('Browser', 'Unknown')}")
        print(f"Protocol: {data.get('Protocol-Version', 'Unknown')}")
except Exception as e:
    print(f"❌ CDP Port Check Failed: {e}")

import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from arka.skills.registry import get_skill_registry

def verify():
    print("Initializing Registry...")
    registry = get_skill_registry()
    registry.scan_and_register()
    
    print(f"\nRegistry contains {len(registry.registry)} skills.")
    print("-" * 40)
    
    for name, skill in registry.registry.items():
        status = "✅ ACTIVE" if skill.is_active else "❌ BROKEN"
        print(f"[{status}] {name}")
        print(f"  Path: {skill.path}")
        if not skill.is_active:
            print(f"  Error: {skill.error}")
            
    print("-" * 40)
    
    # Check repair queue
    queue_path = registry.repair_queue_path
    if queue_path.exists():
        queue = json.loads(queue_path.read_text())
        print(f"Repair Queue: {len(queue)} items")
        for item in queue:
            print(f"  - {item['name']}: {item['error']}")

if __name__ == "__main__":
    verify()

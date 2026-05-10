import sys
import os
# ROOT should be e:\Mark-XXXIX
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

print(f"ROOT: {ROOT}")
print("Starting import check...")
try:
    from core.orchestrator import AgentOrchestrator
    print("AgentOrchestrator imported successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Import failed: {e}")

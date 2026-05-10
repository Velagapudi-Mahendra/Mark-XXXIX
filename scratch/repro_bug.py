
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from actions.web_search import web_search

print("Testing web_search with normal query...")
res = web_search({"query": "NVIDIA stock price"})
print(f"Result length: {len(res)}")

print("\nTesting web_search with dictionary query (simulating error)...")
try:
    res = web_search({"query": {"some": "dict"}})
    print(f"Result length: {len(res)}")
except Exception as e:
    print(f"Caught expected error: {e}")

print("\nTesting web_search with items as dict...")
try:
    res = web_search({"mode": "compare", "items": {"apple": 1, "orange": 2}, "aspect": "price"})
    print(f"Result length: {len(res)}")
except Exception as e:
    print(f"Caught error: {e}")

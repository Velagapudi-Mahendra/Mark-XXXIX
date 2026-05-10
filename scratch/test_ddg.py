try:
    from ddgs import DDGS
    print("--- Testing ddgs ---")
    with DDGS() as ddgs:
        results = list(ddgs.text("NVIDIA stock price", max_results=3))
        print(f"ddgs results: {len(results)}")
        for r in results:
            print(f" - {r.get('title')}")
except Exception as e:
    print(f"ddgs failed: {e}")

try:
    from duckduckgo_search import DDGS
    print("\n--- Testing duckduckgo_search ---")
    with DDGS() as ddgs:
        results = list(ddgs.text("NVIDIA stock price", max_results=3))
        print(f"duckduckgo_search results: {len(results)}")
except Exception as e:
    print(f"duckduckgo_search failed: {e}")

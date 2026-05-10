import os
import sys
from pathlib import Path

# Ensure core module can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.llm_provider import generate_text, _load_config

def main():
    print("Testing NVIDIA GLM-4 Fallback...")
    print("We will intentionally pass a bad Gemini API key to force a failure.")
    
    # We monkey-patch the config loading to return a bad gemini key
    original_load_config = _load_config
    
    def fake_load_config():
        config = original_load_config()
        config['gemini_api_key'] = "INVALID_KEY_TO_FORCE_ERROR"
        return config

    import core.llm_provider
    core.llm_provider._load_config = fake_load_config
    
    try:
        response = generate_text(
            prompt="Explain the theory of relativity in 2 short sentences.",
            system_instruction="You are a helpful physics teacher."
        )
        print("\n\n--- Final Response Returned ---")
        print(response)
    except Exception as e:
        print(f"\nTest failed with error: {e}")

if __name__ == "__main__":
    main()

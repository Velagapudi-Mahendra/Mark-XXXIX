import json
import os
import sys
import google.generativeai as genai
from openai import OpenAI
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_text(prompt: str, system_instruction: str = "", model_name: str = "gemini-2.5-flash", force_nvidia: bool = False, nvidia_model: str = "z-ai/glm4.7") -> str:
    """
    Generates text using Gemini with an automatic fallback to NVIDIA (GLM-4) if Gemini fails.
    If force_nvidia is True, it skips Gemini entirely.
    """
    config = _load_config()
    gemini_key = config.get("gemini_api_key")
    nvidia_key = config.get("nvidia_api_key")

    if force_nvidia:
        print(f"[LLM] Explicitly using NVIDIA Integrated API ({nvidia_model})...")
        return _generate_with_nvidia(prompt, system_instruction, nvidia_key, nvidia_model)

    # Try Gemini First
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction if system_instruction else None
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        error_str = str(e)
        print(f"[LLM] Gemini failed: {error_str[:100]}...")
        # Fallback to NVIDIA if Gemini fails with rate limit or quota errors
        is_rate_limit = any(x in error_str.lower() for x in ["429", "quota", "limit", "rate_limit", "exhausted"])
        if is_rate_limit:
            print(f"[LLM] Falling back to NVIDIA Integrated API ({nvidia_model})...")
            return _generate_with_nvidia(prompt, system_instruction, nvidia_key, nvidia_model)
        
        raise e

_USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
_REASONING_COLOR = "\033[90m" if _USE_COLOR else ""
_RESET_COLOR = "\033[0m" if _USE_COLOR else ""

def _generate_with_nvidia(prompt: str, system_instruction: str, api_key: str, model_name: str = "z-ai/glm4.7") -> str:
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=1,
            top_p=1,
            max_tokens=16384,
            extra_body={"chat_template_kwargs": {"enable_thinking": True, "clear_thinking": False}},
            stream=True
        )
        
        full_content = ""
        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                print(f"{_REASONING_COLOR}{reasoning}{_RESET_COLOR}", end="", flush=True)
            content_chunk = getattr(delta, "content", None)
            if content_chunk is not None:
                print(content_chunk, end="", flush=True)
                full_content += content_chunk
        
        print(flush=True) # Add a newline after streaming is complete
        return full_content.strip()
    except Exception as e:
        print(f"[LLM] NVIDIA fallback also failed: {e}", flush=True)
        raise e

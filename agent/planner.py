import json
import re
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


PLANNER_PROMPT = """You are the planning module of MARK XXV, a personal AI assistant.
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- NEVER use generated_code or write Python scripts. It does not exist.
- NEVER reference previous step results in parameters. Every step is independent.
- Use web_search for ANY information retrieval, research, or current data.
- Use file_controller to save content to disk.
- Max 5 steps. Use the minimum steps needed.

AVAILABLE TOOLS AND THEIR PARAMETERS:

open_app
  app_name: string (required)

web_search
  query: string (required) — write a clear, focused search query
  mode: "search" or "compare" (optional, default: search)
  items: list of strings (optional, for compare mode)
  aspect: string (optional, for compare mode)

game_updater
  action: "update" | "install" | "list" | "download_status" | "schedule" (required)
  platform: "steam" | "epic" | "both" (optional, default: both)
  game_name: string (optional)
  app_id: string (optional)
  shutdown_when_done: boolean (optional)

browser_control
  action: "go_to" | "search" | "click" | "type" | "scroll" | "get_text" | "press" | "close" (required)
  url: string (for go_to)
  query: string (for search)
  text: string (for click/type)
  direction: "up" | "down" (for scroll)

file_controller
  action: "write" | "create_file" | "read" | "list" | "delete" | "move" | "copy" | "find" | "disk_usage" (required)
  path: string — use "desktop" for Desktop folder
  name: string — filename
  content: string — file content (for write/create_file)

computer_settings
  action: string (required)
  description: string — natural language description
  value: string (optional)

computer_control
  action: "type" | "click" | "hotkey" | "press" | "scroll" | "screenshot" | "screen_find" | "screen_click" (required)
  text: string (for type)
  x, y: int (for click)
  keys: string (for hotkey, e.g. "ctrl+c")
  key: string (for press)
  direction: "up" | "down" (for scroll)
  description: string (for screen_find/screen_click)

screen_process
  text: string (required) — what to analyze or ask about the screen
  angle: "screen" | "camera" (optional)

send_message
  receiver: string (required)
  message_text: string (required)
  platform: string (required)

reminder
  date: string YYYY-MM-DD (required)
  time: string HH:MM (required)
  message: string (required)

desktop_control
  action: "wallpaper" | "organize" | "clean" | "list" | "task" (required)
  path: string (optional)
  task: string (optional)

youtube_video
  action: "play" | "summarize" | "trending" (required)
  query: string (for play)

weather_report
  city: string (required)

flight_finder
  origin: string (required)
  destination: string (required)
  date: string (required)

code_helper
  action: "write" | "edit" | "run" | "explain" (required)
  description: string (required)
  language: string (optional)
  output_path: string (optional)
  file_path: string (optional)

dev_agent
  description: string (required)
  language: string (optional)
# FIX Bug 1: All examples are now valid JSON matching the output schema.
EXAMPLES:

Goal: "Research mechanical engineering and save it to a file"
{"goal": "Research mechanical engineering and save it to a file", "steps": [
  {"step": 1, "tool": "web_search", "description": "Search for mechanical engineering overview", "parameters": {"query": "mechanical engineering overview definition history applications"}, "dependencies": [], "critical": true},
  {"step": 2, "tool": "file_controller", "description": "Save research to desktop", "parameters": {"action": "write", "path": "desktop", "name": "mechanical_engineering.txt", "content": "MECHANICAL ENGINEERING RESEARCH"}, "dependencies": [1], "critical": false}
]}

Goal: "What is the price of Bitcoin"
{"goal": "What is the price of Bitcoin", "steps": [
  {"step": 1, "tool": "web_search", "description": "Search current Bitcoin price", "parameters": {"query": "Bitcoin price today USD"}, "dependencies": [], "critical": true}
]}

Goal: "List the files on the desktop and find the largest 5"
{"goal": "List the files on the desktop and find the largest 5", "steps": [
  {"step": 1, "tool": "file_controller", "description": "List desktop files", "parameters": {"action": "list", "path": "desktop"}, "dependencies": [], "critical": true},
  {"step": 2, "tool": "file_controller", "description": "Find largest 5 files", "parameters": {"action": "largest", "path": "desktop", "count": 5}, "dependencies": [], "critical": false}
]}

Goal: "Install PUBG from Steam"
{"goal": "Install PUBG from Steam", "steps": [
  {"step": 1, "tool": "game_updater", "description": "Install PUBG via Steam", "parameters": {"action": "install", "platform": "steam", "game_name": "PUBG"}, "dependencies": [], "critical": true}
]}

Goal: "Send John a message on WhatsApp about a meeting tomorrow"
{"goal": "Send John a message on WhatsApp about a meeting tomorrow", "steps": [
  {"step": 1, "tool": "send_message", "description": "Send WhatsApp message to John", "parameters": {"receiver": "John", "message_text": "There is a meeting tomorrow", "platform": "WhatsApp"}, "dependencies": [], "critical": true}
]}

Goal: "Set a reminder for 30 minutes from now"
{"goal": "Set a reminder for 30 minutes from now", "steps": [
  {"step": 1, "tool": "reminder", "description": "Set reminder", "parameters": {"date": "[today]", "time": "[now+30min]", "message": "Reminder"}, "dependencies": [], "critical": true}
]}

OUTPUT — return ONLY valid JSON, no markdown, no explanation, no code blocks:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {},
      "dependencies": [],
      "critical": true
    }
  ]
}
"""


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def create_plan(goal: str, context: str = "") -> dict:
    from core.llm_provider import generate_text

    user_input = f"Goal: {goal}"
    if context:
        user_input += f"\n\nContext: {context}"

    try:
        text = generate_text(user_input, system_instruction=PLANNER_PROMPT, force_nvidia=True)
        text     = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        plan = json.loads(text)

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Invalid plan structure")

        for step in plan["steps"]:
            if step.get("tool") in ("generated_code",):
                print(f"[Planner] WARN generated_code detected in step {step.get('step')} - replacing with web_search")
                desc = step.get("description", goal)
                step["tool"] = "web_search"
                step["parameters"] = {"query": desc[:200]}

        print(f"[Planner] OK Plan: {len(plan['steps'])} steps")
        for s in plan["steps"]:
            print(f"  Step {s['step']}: [{s['tool']}] {s['description']}")

        return plan

    except json.JSONDecodeError as e:
        print(f"[Planner] WARN JSON parse failed: {e}")
        return _fallback_plan(goal)
    except Exception as e:
        print(f"[Planner] WARN Planning failed: {e}")
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    # FIX Bug 2: every step dict now includes "dependencies" key.
    print("[Planner] RETRY Fallback plan (Enhanced)")
    has_save = any(w in goal.lower() for w in ["write", "save", "file", "desktop"])
    steps = [
        {
            "step": 1,
            "tool": "web_search",
            "description": f"Research: {goal}",
            "parameters": {"query": goal[:200]},
            "dependencies": [],        # FIX Bug 2
            "critical": True,
        }
    ]
    if has_save:
        steps.append({
            "step": 2,
            "tool": "file_controller",
            "description": "Save research results to desktop",
            "parameters": {"action": "write", "path": "desktop", "name": "research_results.txt"},
            "dependencies": [1],       # FIX Bug 2 (was already here, kept)
            "critical": False,
        })
    return {"goal": goal, "steps": steps}


def generate_structured_plan(goal: str) -> dict:
    """
    New method (feature requirement): returns a plan using 'args' and
    'depends_on' keys (ToolRegistry-friendly schema).
    Internally delegates to create_plan and transforms the result.
    Falls back to a safe single-step plan on any error.
    """
    try:
        raw = create_plan(goal)
        structured_steps = []
        for s in raw.get("steps", []):
            structured_steps.append({
                "step":       s["step"],
                "tool":       s["tool"],
                "description": s.get("description", ""),
                "args":       s.get("parameters", {}),   # renamed
                "depends_on": s.get("dependencies", []), # renamed
                "critical":   s.get("critical", True),
            })
        return {"goal": goal, "steps": structured_steps}
    except Exception as e:
        print(f"[Planner] generate_structured_plan failed: {e} — using fallback")
        return {
            "goal": goal,
            "steps": [
                {"step": 1, "tool": "web_search",
                 "args": {"query": goal[:200]}, "depends_on": [],
                 "description": f"Research: {goal}", "critical": True}
            ],
        }


def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    from core.llm_provider import generate_text

    completed_summary = "\n".join(
        f"  - Step {s['step']} ({s['tool']}): DONE" for s in completed_steps
    )

    prompt = f"""Goal: {goal}

Already completed:
{completed_summary if completed_summary else '  (none)'}

Failed step: [{failed_step.get('tool')}] {failed_step.get('description')}
Error: {error}

Create a REVISED plan for the remaining work only. Do not repeat completed steps."""

    try:
        text = generate_text(prompt, system_instruction=PLANNER_PROMPT, force_nvidia=True)
        text     = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan     = json.loads(text)

        for step in plan.get("steps", []):
            if step.get("tool") == "generated_code":
                step["tool"] = "web_search"
                step["parameters"] = {"query": step.get("description", goal)[:200]}

        print(f"[Planner] RETRY Revised plan: {len(plan['steps'])} steps")
        return plan
    except Exception as e:
        print(f"[Planner] WARN Replan failed: {e}")
        return _fallback_plan(goal)

def extract_technical_details(goal: str, steps: list, results: dict) -> dict:
    """
    Chronicler Phase: Extracts technical facts from completed task results.
    Uses NVIDIA (GLM-4) to reason about project details.
    """
    from core.llm_provider import generate_text

    # Prepare a condensed summary of what happened
    history = []
    for s in steps:
        sid = str(s["step"])
        res = results.get(sid, "")
        history.append(f"Step {sid} ({s['tool']}): {s['description']}\nResult: {str(res)[:500]}")

    prompt = f"""You are the MARK-XXXIX Technical Chronicler.
Review the following completed task and extract ONLY project-specific technical facts.

USER GOAL: {goal}
TASK EXECUTION LOG:
{"\n---\n".join(history)}

Identify and extract:
1. Tech stack (languages, frameworks, libraries used/detected).
2. Important file paths or directory structures mentioned.
3. Naming conventions or architectural patterns observed.
4. Project-level goals or constraints discovered.

Output ONLY a JSON object where keys are short descriptors and values are the specific facts.
Example: {{"tech_stack": "Python 3.12, FastAPI", "main_entry": "main.py"}}
If no new technical details are found, return {{}}.
Max 256 tokens."""

    try:
        # Use NVIDIA GLM-4 as requested for high reasoning
        text = generate_text(prompt, system_instruction="You are a technical data extractor.", force_nvidia=True)
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        
        extracted = json.loads(text)
        if not isinstance(extracted, dict):
            return {}
        
        print(f"[Chronicler] Extracted {len(extracted)} technical facts.")
        return extracted
    except Exception as e:
        print(f"[Chronicler] Extraction failed: {e}")
        return {}

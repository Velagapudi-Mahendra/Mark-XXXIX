"""
core/tool_registry.py  —  Central tool registry for AgentOrchestrator.
All action modules register themselves here so the orchestrator can call
them by name without hard-coded imports.
"""
from typing import Any, Callable, Dict


class ToolRegistry:
    """Maps tool names to callable action functions."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable) -> None:
        self._tools[name] = func
        print(f"[ToolRegistry] Registered: {name}")

    def execute(self, name: str, args: dict) -> Any:
        if name not in self._tools:
            raise ValueError(f"[ToolRegistry] Unknown tool: '{name}'")
        return self._tools[name](parameters=args)

    def list_tools(self) -> list:
        return list(self._tools.keys())


# ── Singleton ──────────────────────────────────────────────────────────────
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    return _registry


def register_default_tools() -> None:
    """Register all standard action modules into the global registry."""
    _pairs = [
        ("web_search",       "actions.web_search",       "web_search"),
        ("file_controller",  "actions.file_controller",  "file_controller"),
        ("open_app",         "actions.open_app",         "open_app"),
        ("weather_report",   "actions.weather_report",   "weather_action"),
        ("browser_control",  "actions.browser_control",  "browser_control"),
        ("computer_control", "actions.computer_control", "computer_control"),
        ("youtube_video",    "actions.youtube_video",    "youtube_video"),
        ("send_message",     "actions.send_message",     "send_message"),
        ("reminder",         "actions.reminder",         "reminder"),
        ("desktop_control",  "actions.desktop",          "desktop_control"),
        ("computer_settings","actions.computer_settings","computer_settings"),
        ("code_helper",      "actions.code_helper",      "code_helper"),
        ("dev_agent",        "actions.dev_agent",        "dev_agent"),
        ("flight_finder",    "actions.flight_finder",    "flight_finder"),
        ("game_updater",     "actions.game_updater",     "game_updater"),
    ]
    for reg_name, module_path, func_name in _pairs:
        # browser_control fallback logic for agent-browser
        if reg_name == "browser_control":
            import shutil
            if shutil.which("agent-browser"):
                print("[ToolRegistry] agent-browser found on PATH. Using native BrowserAgent.")
                module_path = "actions.browser_agent"
                func_name = "browser_agent_action"
            else:
                print("[ToolRegistry] ⚠️ agent-browser not found. Falling back to legacy Playwright browser_control.")
                
        try:
            mod = __import__(module_path, fromlist=[func_name])
            _registry.register(reg_name, getattr(mod, func_name))
        except Exception as e:
            print(f"[ToolRegistry] Could not register '{reg_name}': {e}")

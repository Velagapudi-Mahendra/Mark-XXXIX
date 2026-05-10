import subprocess
import json
import logging
import shutil
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class BrowserAgent:
    """
    Wraps the native agent-browser CLI for AI tasks.
    Uses the client-daemon architecture for fast, deterministic interactions.
    """
    def execute(self, command: List[str]) -> Dict[str, Any]:
        """
        Low-level fallback to run any agent-browser command with --json.
        """
        cmd = ["agent-browser"] + command + ["--json"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"success": True, "raw_output": result.stdout}
        except subprocess.CalledProcessError as e:
            try:
                err_data = json.loads(e.stdout)
                return {"success": False, "error": err_data.get("error", e.stderr)}
            except json.JSONDecodeError:
                return {"success": False, "error": e.stderr or str(e)}
        except FileNotFoundError:
            return {"success": False, "error": "agent-browser not found in PATH."}

    def browse(self, url: str) -> bool:
        """Navigates the browser to the given URL."""
        res = self.execute(["open", url])
        return res.get("success", False)

    def snapshot(self, interactive: bool = True) -> List[Dict[str, Any]]:
        """
        Gets a structured JSON tree of elements, returning a list of interactive elements.
        """
        cmd = ["snapshot"]
        if interactive:
            cmd.append("-i")
        
        res = self.execute(cmd)
        if not res.get("success", True): # Assume success if missing but JSON parsed
             return []
        
        elements = res.get("elements", [])
        # If output is not standard dictionary, return raw list if it is a list
        if isinstance(res, list):
            return res
        return elements

    def click(self, ref: str) -> bool:
        """Clicks an element using its snapshot ref (e.g. @e1)."""
        res = self.execute(["click", ref])
        return res.get("success", False)

    def fill(self, ref: str, text: str) -> bool:
        """Fills a text field using its snapshot ref (e.g. @e1)."""
        res = self.execute(["fill", ref, text])
        return res.get("success", False)

    def screenshot(self, path: str) -> bool:
        """Takes a screenshot and saves it to the given path."""
        res = self.execute(["screenshot", path])
        return res.get("success", False)

    def close(self) -> bool:
        """Closes the browser daemon."""
        res = self.execute(["close"])
        return res.get("success", False)

_browser_agent = BrowserAgent()

def browser_agent_action(parameters: dict, player=None) -> str:
    """
    Main entry point for the orchestrator to interact with the new BrowserAgent.
    """
    action = parameters.get("action")
    if not action:
        return "Error: No action provided."
        
    try:
        if action == "open" or action == "go_to":
            url = parameters.get("url", "about:blank")
            success = _browser_agent.browse(url)
            return f"Navigated to {url}" if success else f"Failed to open {url}"
            
        elif action == "snapshot":
            elements = _browser_agent.snapshot(interactive=True)
            return json.dumps(elements, indent=2)
            
        elif action == "click":
            ref = parameters.get("ref") or parameters.get("selector")
            if not ref:
                return "Error: Element ref required for click."
            success = _browser_agent.click(ref)
            return f"Clicked element {ref}" if success else f"Failed to click {ref}"
            
        elif action == "type" or action == "fill" or action == "fill_form":
            ref = parameters.get("ref") or parameters.get("selector")
            text = parameters.get("text", "")
            if not ref:
                return "Error: Element ref required for fill/type."
            success = _browser_agent.fill(ref, text)
            return f"Filled element {ref} with text" if success else f"Failed to fill {ref}"
            
        elif action == "screenshot":
            path = parameters.get("path", "screenshot.png")
            success = _browser_agent.screenshot(path)
            return f"Screenshot saved to {path}" if success else "Failed to take screenshot."
            
        elif action == "close":
            success = _browser_agent.close()
            return "Browser closed." if success else "Failed to close browser."
            
        else:
            return f"Unknown action: {action}. Supported: open, snapshot, click, type/fill, screenshot, close."
            
    except Exception as e:
        return f"Browser agent error: {str(e)}"

def check_installation() -> bool:
    """Check if agent-browser is available on PATH."""
    return shutil.which("agent-browser") is not None

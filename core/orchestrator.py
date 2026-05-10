"""
core/orchestrator.py  —  AgentOrchestrator
Manages complex multi-step goals as a DAG with persistence and retry.

Bugs fixed here:
  Bug 3  – set HUD state to ORCHESTRATING / LISTENING
  Bug 4  – send "error" (not "failed") to TaskStepWidget
  Bug 5  – removed fragile string-based success check
  Bug 7  – pass self.ui as player so tools can log to HUD
  Bug 8  – has_resumable_state() + improved resume path
  Bug 9  – _sanitize_params: placeholder replacement + type coercion
"""

import os
import json
import re
import threading
import concurrent.futures
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# NOTE: agent.planner and agent.executor are imported lazily inside methods
# to avoid pulling in Google genai / sounddevice at test-import time.


class AgentOrchestrator:
    """
    Executes a multi-step goal via a dependency-aware DAG.
    State is persisted to disk so tasks survive restarts.
    """

    STATE_FILE = Path("state/orchestrator.json")

    def __init__(self, ui=None, speak: Callable = None, skill_manager=None):
        self.ui     = ui
        self.speak  = speak
        self.skill_manager = skill_manager
        self.state: Dict[str, Any] = {
            "goal":            "",
            "steps":           [],
            "results":         {},
            "status":          "idle",   # idle | running | completed | failed
            "current_plan_id": None,
        }
        self.cancel_flag = threading.Event()
        self.lock        = threading.RLock()
        self.is_active   = False
        self.executor    = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._load_state()

    # ── Persistence ────────────────────────────────────────────────────────

    def _save_state(self):
        """Thread-safe state serialisation."""
        with self.lock:
            try:
                self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(self.STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, indent=2, default=str)
            except Exception as e:
                print(f"[Orchestrator] Save error: {e}")

    def _load_state(self):
        if self.STATE_FILE.exists():
            try:
                with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.state.update(data)
                    print(f"[Orchestrator] Loaded state — goal: {self.state['goal']!r}")
            except Exception as e:
                print(f"[Orchestrator] Failed to load state: {e}")

    # FIX Bug 8: expose whether a resumable task exists
    def has_resumable_state(self) -> bool:
        return (
            self.STATE_FILE.exists()
            and bool(self.state.get("goal"))
            and self.state.get("status") == "running"
        )

    def clear_state(self):
        self.state = {
            "goal": "", "steps": [], "results": {},
            "status": "idle", "current_plan_id": None,
        }
        if self.STATE_FILE.exists():
            os.remove(self.STATE_FILE)

    def trigger_skill(self, skill_name: str, params: Dict[str, Any]):
        """
        Triggers a pre-defined skill. Resolves placeholders and kicks off orchestration.
        """
        if not self.skill_manager:
            print("[Orchestrator] ❌ SkillManager not initialized.")
            return

        skill = self.skill_manager.resolve_placeholders(skill_name, params)
        if not skill:
            print(f"[Orchestrator] ❌ Skill '{skill_name}' not found or invalid.")
            return

        with self.lock:
            if self.state["status"] == "running":
                print("[Orchestrator] ⚠️ Cannot trigger skill: Another task is running.")
                return

            self.state["goal"]   = f"Skill: {skill.get('description', skill_name)}"
            self.state["steps"]  = skill["steps"]
            self.state["status"] = "running"
            self.state["results"] = {}
            self._save_state()

        # Start execution in background
        threading.Thread(target=self.execute, kwargs={"goal": self.state["goal"], "resume": True}, daemon=True).start()
        print(f"[Orchestrator] [TRIGGER] Triggered skill: {skill_name}")

    # ── Parameter safety ───────────────────────────────────────────────────

    def _sanitize_params(self, params: dict, step_results: dict) -> dict:
        """
        FIX Bug 9:
        1. Replace {{output.N}} placeholders with the actual result of step N.
        2. Coerce any remaining dict/list values to str so action modules
           never receive non-primitive args.
        """
        out = {}
        for key, val in params.items():
            # 1. Placeholder substitution
            if isinstance(val, str):
                def _sub(m):
                    ref = m.group(1)
                    return str(step_results.get(ref, ""))[:2000]
                val = re.sub(r"\{\{output\.(\d+)\}\}", _sub, val)

            # 2. Type coercion
            if isinstance(val, dict):
                print(f"[Orchestrator] WARN param '{key}' is dict — coercing to str")
                val = str(val)
            elif isinstance(val, list):
                val = ", ".join(str(x) for x in val)

            out[key] = val
        return out

    # ── Public API ─────────────────────────────────────────────────────────

    def execute(self, goal: str, resume: bool = False) -> str:
        """High-level entry point to run a task."""
        with self.lock:
            # Concurrency Guard: Only allow one active execution thread at a time
            if self.is_active:
                print(f"[Orchestrator] Orchestrator is already busy with an active task.")
                return "running"

            # Check if this is the same goal already marked as running (resumption)
            # or a brand new goal.
            if self.state.get("goal") != goal:
                print(f"[Orchestrator] New Goal: {goal}")
                self.state = {
                    "goal": goal,
                    "status": "running",
                    "steps": [],
                    "results": {}
                }
            else:
                print(f"[Orchestrator] Executing/Resuming goal: {goal}")
                self.state["status"] = "running"
            
            self.is_active = True
            self._save_state()

            # Offload to background thread
            future = self.executor.submit(self._start_task)
            future.add_done_callback(self._on_execution_done)
            return "running"

    def _on_execution_done(self, future):
        """Callback when the background task finishes."""
        with self.lock:
            self.is_active = False
            try:
                res = future.result()
                if isinstance(res, str) and res.startswith("failed"):
                    self.state["status"] = "failed"
                else:
                    self.state["status"] = "completed" if res == "completed" else "idle"
            except Exception as e:
                print(f"[Orchestrator] Execution thread crashed: {e}")
                self.state["status"] = "failed"
            self._save_state()

    # ── Background Task Flow ───────────────────────────────────────────────

    def _start_task(self) -> str:
        """The main execution loop (runs in background thread)."""
        # Lazy import planner
        from agent.planner import create_plan

        # FIX Bug 3: set HUD state
        if self.ui:
            self.ui.set_state("ORCHESTRATING")

        # 1. Planning (only if no steps exist yet)
        if not self.state["steps"]:
            print(f"[Orchestrator] Planning for goal: {self.state['goal']}")
            try:
                plan = create_plan(self.state["goal"])
                with self.lock:
                    self.state["steps"] = plan.get("steps", [])
                if self.ui:
                    self.ui.set_task_plan(self.state["steps"])
                self._save_state()
            except Exception as e:
                print(f"[Orchestrator] Planning failed: {e}")
                return f"failed: planning error: {e}"

        if not self.state["steps"]:
            if self.ui:
                self.ui.set_state("LISTENING")
            return "failed: no plan"

        # 2. DAG Execution
        outcome = self._run_dag()

        # FIX Bug 3: restore listening state
        if self.ui:
            self.ui.set_state("LISTENING")

        # 3. Chronicler Reflection (if successful and complex)
        if outcome == "completed" and len(self.state["steps"]) > 1:
            try:
                self._run_chronicler()
            except Exception as e:
                print(f"[Orchestrator] Chronicler failed (non-critical): {e}")

        # 4. Summary Generation (if successful)
        if outcome == "completed":
            summary = self._generate_summary()
            if self.speak:
                self.speak(summary)
            return "completed"
        else:
            return f"failed: {outcome}"

    def _run_dag(self) -> str:
        """Dependency-aware step execution loop."""
        steps = self.state["steps"]

        while True:
            if self.cancel_flag.is_set():
                return "cancelled"

            ready = []
            for step in steps:
                sid = str(step["step"])
                if sid in self.state["results"]:
                    continue
                # Support both key names
                deps = step.get("dependencies", step.get("depends_on", []))
                if all(str(d) in self.state["results"] for d in deps):
                    ready.append(step)

            if not ready:
                if len(self.state["results"]) == len(steps):
                    return "completed"
                return "stalled (circular dependency or missing steps)"

            # Execute ready steps in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(ready)) as pool:
                futures = {pool.submit(self._run_step, s): s for s in ready}
                for future in concurrent.futures.as_completed(futures):
                    step  = futures[future]
                    sid   = str(step["step"])
                    try:
                        res = future.result()
                        # If a critical step failed, abort the whole DAG
                        if isinstance(res, Exception) and step.get("critical", True):
                            return f"failed at step {sid}: {res}"
                    except Exception as e:
                        if step.get("critical", True):
                            return f"failed at step {sid}: {e}"

    def _run_step(self, step: Dict[str, Any]):
        """Execute one step with up to 3 attempts."""
        sid   = str(step["step"])
        tool  = step["tool"]
        params = step.get("parameters", step.get("args", {}))
        desc   = step.get("description", f"Step {sid}")

        print(f"[Orchestrator] Step {sid}: [{tool}] {desc}")
        if self.ui:
            self.ui.write_log(f"SYS: Step {sid} — {desc}")
            self.ui.update_task_step(int(sid), "running")
        
        if self.speak:
            self.speak(f"Starting step {sid}: {desc}")

        last_err = None
        for attempt in range(1, 4):
            try:
                with self.lock:
                    current_results = dict(self.state["results"])

                # Sanitize and inject context
                resolved = self._sanitize_params(params, current_results)
                from agent.executor import _inject_context
                resolved = _inject_context(
                    resolved, tool, current_results, goal=self.state["goal"]
                )

                # Call the tool
                from agent.executor import _call_tool
                res = _call_tool(tool, resolved, self.speak, player=self.ui)

                # Success
                with self.lock:
                    self.state["results"][sid] = res
                    self._save_state()

                if self.ui:
                    self.ui.update_task_step(int(sid), "done")
                    self.ui.write_log(f"SYS: Step {sid} completed.")

                return True

            except Exception as e:
                last_err = e
                print(f"[Orchestrator] Step {sid} attempt {attempt} failed: {e}")
                if attempt < 3:
                    import time
                    time.sleep(2 ** attempt)

        # Permanent Failure
        print(f"[Orchestrator] Step {sid} permanently failed: {last_err}")
        if self.ui:
            self.ui.update_task_step(int(sid), "error")

        with self.lock:
            self.state["results"][sid] = f"Error: {last_err}"
            self._save_state()

        return last_err

    # ── Chronicler ─────────────────────────────────────────────────────────

    def _run_chronicler(self):
        """
        Extracts technical facts from the completed task and saves them
        to long-term system knowledge.
        """
        print("[Orchestrator] 🧠 Starting Chronicler reflection phase...")
        from agent.planner import extract_technical_details
        from memory.memory_manager import remember

        goal    = self.state["goal"]
        steps   = self.state["steps"]
        results = self.state["results"]

        technical_facts = extract_technical_details(goal, steps, results)
        
        if not technical_facts:
            print("[Orchestrator] Chronicler: No new technical details extracted.")
            return

        for key, value in technical_facts.items():
            # remember handles normalization and deduplication internally
            remember(key, value, category="system_knowledge")
        
        if self.ui:
            self.ui.write_log(f"SYS: Chronicler saved {len(technical_facts)} technical facts.")

    # ── Summary ────────────────────────────────────────────────────────────

    def _generate_summary(self) -> str:
        goal    = self.state["goal"]
        steps   = self.state["steps"]
        results = self.state["results"]

        try:
            from core.llm_provider import generate_text
            parts = []
            for s in steps:
                sid = str(s["step"])
                r   = results.get(sid, "No result")
                if not str(r).startswith("Error"):
                    parts.append(f"- {s.get('description', s['tool'])}: {str(r)[:300]}")

            prompt = (
                f"User goal: {goal}\n"
                f"Results:\n" + "\n".join(parts) + "\n\n"
                "Summarise concisely as JARVIS. Address the user as 'sir'."
            )
            return generate_text(prompt, model_name="gemini-2.5-flash-lite").strip()
        except Exception:
            return f"Sir, the task '{goal}' has been completed."

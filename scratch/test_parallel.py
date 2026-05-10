
import sys
import os
import time
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set up project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.orchestrator import AgentOrchestrator

class MockUI:
    def __init__(self):
        self.step_starts = {}
    def write_log(self, text):
        if "Orchestrator Step" in text:
            # Extract step ID: "SYS: Orchestrator Step 1 - ..."
            parts = text.split()
            if len(parts) > 3:
                step_id = parts[3]
                self.step_starts[step_id] = time.time()
        print(f"[UI LOG] {text}")
    def set_task_plan(self, plan):
        print(f"[UI PLAN] {plan}")
    def update_task_step(self, step_id, status):
        print(f"[UI STEP] {step_id} -> {status}")
    def set_state(self, state):
        pass

def mock_speak(text):
    print(f"[SPEAK] {text}")

def main():
    goal = "Check the weather in Paris and the NVIDIA stock price at the same time."
    
    ui = MockUI()
    orch = AgentOrchestrator(ui=ui, speak=mock_speak)
    
    # Force a clean state and clear orchestrator file
    if orch.STATE_FILE.exists():
        os.remove(orch.STATE_FILE)
    orch.clear_state()
    
    print(f"\n--- STARTING PARALLEL TEST (v2) ---\nGoal: {goal}\n")
    
    # Define steps
    steps = [
        {"step": 1, "tool": "weather_report", "description": "Weather Paris", "parameters": {"city": "Paris"}, "dependencies": []},
        {"step": 2, "tool": "web_search", "description": "NVDA Stock", "parameters": {"query": "NVDA stock price"}, "dependencies": []}
    ]
    
    # Manually set state to bypass planner call
    orch.state["steps"] = steps
    orch.state["goal"] = goal
    orch.state["status"] = "running"

    # We'll use a slow tool mock to verify parallelism
    def slow_call(tool, params, speak=None):
        print(f"[MOCK] Starting {tool}...")
        time.sleep(3) # Hold for 3 seconds
        print(f"[MOCK] Finished {tool}")
        return "Result ok"

    # Patch both _call_tool and create_plan to be safe
    with patch("core.orchestrator.create_plan", return_value={"goal": goal, "steps": steps}):
        with patch("core.orchestrator._call_tool", side_effect=slow_call) as mock_tool:
            result = orch.execute(goal)
        
    print(f"\n--- FINAL RESULT ---\n{result}\n")
    
    # Check start times
    if "1" in ui.step_starts and "2" in ui.step_starts:
        diff = abs(ui.step_starts["1"] - ui.step_starts["2"])
        print(f"Time difference between step 1 and 2 start: {diff:.4f}s")
        if diff < 1.0:
            print("OK VERIFIED: Steps started simultaneously (Parallel)")
        else:
            print("FAIL: Steps started sequentially")
    else:
        print("FAIL: Could not capture step start times")
        print(f"Captured starts: {ui.step_starts}")

if __name__ == "__main__":
    main()

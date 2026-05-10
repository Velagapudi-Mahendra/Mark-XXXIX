
import sys
import os
import json
from pathlib import Path
import threading

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.skill_manager import SkillManager
from core.orchestrator import AgentOrchestrator

def test_skill_loading():
    print("\n--- Testing Skill Loading ---")
    workspace = Path("C:/Users/mahen/JARVIS_Workspace")
    sm = SkillManager(workspace)
    count = sm.reload_skills()
    print(f"Loaded {count} skills.")
    for s in sm.list_skills():
        print(f" - {s['name']}: {s['description']}")
    return count > 0

def test_placeholder_resolution():
    print("\n--- Testing Placeholder Resolution ---")
    workspace = Path("C:/Users/mahen/JARVIS_Workspace")
    sm = SkillManager(workspace)
    
    user_params = {"location": "London", "interests": "Quantum Computing"}
    resolved = sm.resolve_placeholders("morning_brief", user_params)
    
    if not resolved:
        print("❌ Skill resolution failed.")
        return False
        
    step1_query = resolved["steps"][0]["args"]["query"]
    print(f"Step 1 Query: {step1_query}")
    
    if "London" in step1_query and "{{output.1}}" in json.dumps(resolved):
        print("[SUCCESS] Placeholder resolution successful.")
        return True
    else:
        print("[FAIL] Resolution check failed.")
        return False

def test_orchestrator_trigger():
    print("\n--- Testing Orchestrator Trigger ---")
    # Mock UI and speak
    orch = AgentOrchestrator(ui=None, speak=lambda x: print(f"Speak: {x}"))
    workspace = Path("C:/Users/mahen/JARVIS_Workspace")
    sm = SkillManager(workspace)
    orch.skill_manager = sm
    
    # Clear state first
    orch.clear_state()
    
    orch.trigger_skill("morning_brief", {"location": "Mars", "interests": "Robots"})
    
    print(f"Orchestrator Status: {orch.state['status']}")
    print(f"Orchestrator Goal: {orch.state['goal']}")
    
    if orch.state["status"] == "running" and "Synthesizes" in orch.state.get("goal", ""):
        print("[SUCCESS] Orchestrator triggered successfully.")
        # Cancel execution to avoid actual tool calls in test
        orch.cancel_flag.set()
        return True
    return False

if __name__ == "__main__":
    try:
        s1 = test_skill_loading()
        s2 = test_placeholder_resolution()
        s3 = test_orchestrator_trigger()
        
        if s1 and s2 and s3:
            print("\n*** ALL TESTS PASSED ***")
        else:
            print("\n!!! SOME TESTS FAILED !!!")
    except Exception as e:
        print(f"\n[CRASH] Test crashed: {e}")
        import traceback
        traceback.print_exc()

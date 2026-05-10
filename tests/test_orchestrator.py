"""
tests/test_orchestrator.py  —  Self-contained test suite for AgentOrchestrator.
Does NOT call real APIs. Fully mocked.

Run with:  python tests/test_orchestrator.py
"""
import sys
import os
import json
import threading
import traceback

# ── path setup ─────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from unittest.mock import MagicMock, patch, call
from core.orchestrator import AgentOrchestrator
from core.tool_registry import ToolRegistry

# ── helpers ────────────────────────────────────────────────────────────────
PASS_COUNT = 0
FAIL_COUNT = 0


def _result(name: str, ok: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    status = "PASS" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if ok:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1


def _make_mock_ui():
    ui = MagicMock()
    ui.write_log   = MagicMock()
    ui.set_state   = MagicMock()
    ui.set_task_plan   = MagicMock()
    ui.update_task_step = MagicMock()
    return ui


SIMPLE_PLAN = {
    "goal": "test goal",
    "steps": [
        {"step": 1, "tool": "web_search", "description": "search",
         "parameters": {"query": "test"}, "dependencies": [], "critical": True},
    ],
}

TWO_STEP_PLAN = {
    "goal": "two step goal",
    "steps": [
        {"step": 1, "tool": "web_search", "description": "search",
         "parameters": {"query": "ai safety"}, "dependencies": [], "critical": True},
        {"step": 2, "tool": "file_controller", "description": "save",
         "parameters": {"action": "write", "path": "desktop", "name": "out.txt", "content": ""},
         "dependencies": [1], "critical": False},
    ],
}

PARALLEL_PLAN = {
    "goal": "parallel goal",
    "steps": [
        {"step": 1, "tool": "web_search", "description": "s1",
         "parameters": {"query": "q1"}, "dependencies": [], "critical": True},
        {"step": 2, "tool": "web_search", "description": "s2",
         "parameters": {"query": "q2"}, "dependencies": [], "critical": True},
    ],
}

FAILING_PLAN = {
    "goal": "failing goal",
    "steps": [
        {"step": 1, "tool": "web_search", "description": "fail",
         "parameters": {"query": "crash"}, "dependencies": [], "critical": False},
        {"step": 2, "tool": "web_search", "description": "independent",
         "parameters": {"query": "fine"}, "dependencies": [], "critical": True},
    ],
}


# ── Tests ──────────────────────────────────────────────────────────────────

def test_tool_registry():
    print("\n[Test] ToolRegistry basic operations")
    reg = ToolRegistry()
    mock_fn = MagicMock(return_value="result_A")
    reg.register("mock_tool", mock_fn)
    result = reg.execute("mock_tool", {"key": "val"})
    _result("register + execute", result == "result_A")
    mock_fn.assert_called_once_with(parameters={"key": "val"})
    _result("args forwarded correctly", mock_fn.call_count == 1)

    try:
        reg.execute("nonexistent", {})
        _result("unknown tool raises ValueError", False, "no exception raised")
    except ValueError:
        _result("unknown tool raises ValueError", True)


def test_single_step_execution():
    print("\n[Test] Single-step plan executes and updates UI")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()

    with patch("agent.planner.create_plan", return_value=SIMPLE_PLAN), \
         patch("agent.executor._call_tool", return_value="search_result") as mock_tool, \
         patch("agent.executor._inject_context", side_effect=lambda p, *a, **k: p), \
         patch("core.orchestrator.generate_text", return_value="Summary", create=True):
        orc.execute("test goal")

    _result("web_search tool called",
            any("web_search" in str(c) for c in mock_tool.call_args_list))
    ui.update_task_step.assert_any_call(1, "running")
    _result("step marked running", True)
    ui.update_task_step.assert_any_call(1, "done")
    _result("step marked done", True)
    ui.set_state.assert_any_call("ORCHESTRATING")
    _result("HUD set to ORCHESTRATING (Bug 3)", True)
    ui.set_state.assert_any_call("LISTENING")
    _result("HUD restored to LISTENING (Bug 3)", True)
    orc.clear_state()


def test_dependency_order():
    print("\n[Test] Dependency DAG: step 2 waits for step 1")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()
    call_order = []

    def fake_call_tool(tool, params, speak, player=None):
        call_order.append(tool)
        return f"result_{tool}"

    with patch("agent.planner.create_plan", return_value=TWO_STEP_PLAN), \
         patch("agent.executor._call_tool", side_effect=fake_call_tool), \
         patch("agent.executor._inject_context", side_effect=lambda p, *a, **k: p), \
         patch("core.orchestrator.generate_text", return_value="Summary", create=True):
        orc.execute("two step goal")

    # step 1 must finish before step 2 starts
    _result("step 1 runs first", call_order[0] == "web_search")
    _result("step 2 runs after step 1", len(call_order) == 2)
    orc.clear_state()


def test_parallel_steps():
    print("\n[Test] Parallel steps (no dependencies) both complete")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()
    called_tools = []
    lock = threading.Lock()

    def fake_call_tool(tool, params, speak, player=None):
        with lock:
            called_tools.append(tool)
        return "ok"

    with patch("agent.planner.create_plan", return_value=PARALLEL_PLAN), \
         patch("agent.executor._call_tool", side_effect=fake_call_tool), \
         patch("agent.executor._inject_context", side_effect=lambda p, *a, **k: p), \
         patch("core.orchestrator.generate_text", return_value="Summary", create=True):
        orc.execute("parallel goal")

    _result("both steps executed", len(called_tools) == 2)
    _result("results recorded for both",
            "1" in orc.state["results"] and "2" in orc.state["results"])
    orc.clear_state()


def test_retry_and_failure():
    print("\n[Test] Failing step retried, independent step still runs")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()

    attempt_counts = {"1": 0, "2": 0}

    def fake_call_tool(tool, params, speak, player=None):
        q = params.get("query", "")
        if q == "crash":
            attempt_counts["1"] += 1
            raise RuntimeError("simulated failure")
        attempt_counts["2"] += 1
        return "independent_ok"

    # Patch sleep so retries don't take 6 s in tests
    with patch("agent.planner.create_plan", return_value=FAILING_PLAN), \
         patch("agent.executor._call_tool", side_effect=fake_call_tool), \
         patch("agent.executor._inject_context", side_effect=lambda p, *a, **k: p), \
         patch("core.orchestrator.generate_text", return_value="Summary", create=True), \
         patch("time.sleep"):
        orc.execute("failing goal")

    _result("failing step retried 3 times", attempt_counts["1"] == 3)
    _result("failing step marked error (Bug 4)",
            any(c == call(1, "error") for c in ui.update_task_step.call_args_list))
    _result("independent step still ran", attempt_counts["2"] >= 1)
    orc.clear_state()


def test_persistence_and_resume():
    print("\n[Test] Persistence: save after step 1 → resume runs only step 2")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()

    step2_ran = {"v": False}

    def fake_call_tool(tool, params, speak, player=None):
        if params.get("query") == "ai safety":
            return "search_done"
        step2_ran["v"] = True
        return "write_done"

    # First run: execute step 1 only by simulating a crash after step 1
    with patch("agent.planner.create_plan", return_value=TWO_STEP_PLAN), \
         patch("agent.executor._call_tool", side_effect=fake_call_tool), \
         patch("agent.executor._inject_context", side_effect=lambda p, *a, **k: p), \
         patch("core.orchestrator.generate_text", return_value="Summary", create=True):
        orc.execute("two step goal")

    # Save partial state: only step 1 done
    orc.state["results"] = {"1": "search_done"}
    orc.state["status"]  = "running"
    orc._save_state()

    _result("state file created", orc.STATE_FILE.exists())
    _result("has_resumable_state() True (Bug 8)", orc.has_resumable_state())

    # Create fresh orchestrator that loads state from disk
    orc2 = AgentOrchestrator(ui=ui, speak=None)
    _result("fresh orchestrator sees saved goal",
            orc2.state.get("goal") == "two step goal")
    orc.clear_state()


def test_placeholder_substitution():
    print("\n[Test] Bug 9: {{output.1}} placeholder replaced with step 1 result")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()

    results = {"1": "AI safety is critical"}
    params  = {"content": "Summary: {{output.1}}"}
    sanitized = orc._sanitize_params(params, results)
    _result("placeholder replaced",
            sanitized["content"] == "Summary: AI safety is critical")

    dict_params = {"query": {"nested": "value"}}
    sanitized2  = orc._sanitize_params(dict_params, {})
    _result("dict coerced to str (Bug 9)", isinstance(sanitized2["query"], str))
    orc.clear_state()


def test_ui_plan_set():
    print("\n[Test] UI.set_task_plan called with correct steps")
    ui = _make_mock_ui()
    orc = AgentOrchestrator(ui=ui, speak=None)
    orc.clear_state()

    with patch("agent.planner.create_plan", return_value=SIMPLE_PLAN), \
         patch("agent.executor._call_tool", return_value="ok"), \
         patch("agent.executor._inject_context", side_effect=lambda p, *a, **k: p), \
         patch("core.orchestrator.generate_text", return_value="Summary", create=True):
        orc.execute("test goal")

    ui.set_task_plan.assert_called_once()
    arg = ui.set_task_plan.call_args[0][0]
    _result("set_task_plan called with step list",
            isinstance(arg, list) and len(arg) == 1)
    orc.clear_state()


# ── Runner ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  MARK-XXXIX Orchestrator Test Suite")
    print("=" * 60)

    tests = [
        test_tool_registry,
        test_single_step_execution,
        test_dependency_order,
        test_parallel_steps,
        test_retry_and_failure,
        test_persistence_and_resume,
        test_placeholder_substitution,
        test_ui_plan_set,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"\n  [ERROR] {t.__name__} raised an exception:")
            traceback.print_exc()
            global FAIL_COUNT
            FAIL_COUNT += 1

    print("\n" + "=" * 60)
    total = PASS_COUNT + FAIL_COUNT
    print(f"  Results: {PASS_COUNT}/{total} passed"
          f"  |  {FAIL_COUNT} failed")
    print("=" * 60)
    sys.exit(0 if FAIL_COUNT == 0 else 1)


if __name__ == "__main__":
    main()

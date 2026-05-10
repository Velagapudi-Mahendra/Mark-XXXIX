# Implementation Plan: Mark-XXXIX Major Expansion

This plan outlines the steps to implement four major features: Advanced Agent Task Orchestration, Enhanced Real-time Context Management, Seamless Multimodal Integration, and Proactive Automation.

## Overview
- **Project Type**: BACKEND/UI (Python + PyQt6)
- **Goal**: Transform Mark-XXXIX into a fully autonomous, context-aware, multimodal agent system.

## Proposed Changes

### Phase 1: Foundation & Context (Core Infrastructure)
- [ ] **Task 1: Tool Registry**
  - Create `core/tool_registry.py`.
  - Implement dynamic scanning of `actions/` folder.
  - Agent: `backend-specialist`
- [ ] **Task 2: Habits Memory**
  - Update `memory/memory_manager.py` to include `habits` category.
  - Implement `log_habit` function.
  - Agent: `backend-specialist`
- [ ] **Task 3: Local Memory Retriever**
  - Create `memory/retriever.py`.
  - Implement TF-IDF + Cosine Similarity for local retrieval.
  - Agent: `backend-specialist`
- [ ] **Task 4: Context Manager**
  - Create `core/context_manager.py`.
  - Implement session logs, expiring references, and `inject_context`.
  - Agent: `backend-specialist`

### Phase 2: Intelligence & Orchestration
- [ ] **Task 5: Structured Planner**
  - Modify `agent/planner.py` to output JSON plans.
  - Agent: `backend-specialist`
- [ ] **Task 6: DAG Orchestrator**
  - Create `core/orchestrator.py`.
  - Implement DAG construction, persistence to `state/orchestrator.json`, and execution loop.
  - Agent: `orchestrator`
- [ ] **Task 7: Task Executor Update**
  - Modify `agent/executor.py` to support granular step execution for the Orchestrator.
  - Agent: `backend-specialist`

### Phase 3: Multimodal & Proactive Systems
- [ ] **Task 8: Multimodal Fusion**
  - Create `core/multimodal_fusion.py`.
  - Implement unified Gemini call with image + text + audio context.
  - Agent: `backend-specialist`
- [ ] **Task 9: Proactivity Engine**
  - Create `core/proactivity_engine.py`.
  - Implement background thread, pattern detection, and trust model (ask first 3 times).
  - Agent: `backend-specialist`

### Phase 4: Integration & UI
- [ ] **Task 10: Prompt Placeholders**
  - Update `core/prompt.txt` with `{{SESSION_HISTORY}}` and `{{RELEVANT_MEMORIES}}`.
  - Agent: `backend-specialist`
- [ ] **Task 11: Main Loop Integration**
  - Modify `main.py` to use Orchestrator, ContextManager, and Multimodal Fusion.
  - Implement "Clear Context" voice command.
  - Agent: `orchestrator`
- [ ] **Task 12: UI HUD Update**
  - Modify `ui.py` to add Progress Panel, Suggestion Bar, and Status Indicators.
  - Agent: `frontend-specialist`

## Verification (Phase X)
- [ ] Run `python .agent/scripts/checklist.py .`
- [ ] Verify Orchestrator state persistence by killing/restarting during a task.
- [ ] Verify Memory retrieval returns relevant facts for a given prompt.
- [ ] Verify Proactivity suggestion bar appears after 3 repeated actions.
- [ ] Verify Multimodal fusion captures screen on voice trigger.

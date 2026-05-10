
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.orchestrator import AgentOrchestrator
from memory.memory_manager import load_memory, save_memory

class TestChroniclerIntegration(unittest.TestCase):
    
    @patch("agent.planner.generate_structured_plan")
    @patch("agent.planner.extract_technical_details")
    @patch("core.orchestrator.AgentOrchestrator._run_step")
    def test_full_flow_with_chronicler(self, mock_run_step, mock_extract, mock_plan):
        # 1. Setup Mock UI
        mock_ui = MagicMock()
        
        # 2. Setup Mock Plan (2 steps to trigger chronicler)
        mock_plan.return_value = {
            "steps": [
                {"step": 1, "tool": "file_processor", "description": "Analyzing tech stack"},
                {"step": 2, "tool": "code_helper", "description": "Applying conventions"}
            ]
        }
        
        # 3. Setup Mock Step Results
        mock_run_step.return_value = "Step successful"
        
        # 4. Setup Mock Extraction Results
        mock_extract.return_value = {
            "tech_stack": "Python 3.12, PyQt6",
            "naming_convention": "PEP8"
        }
        
        # 5. Initialize Orchestrator
        orch = AgentOrchestrator(ui=mock_ui)
        
        # 6. Clear test memory
        memory = load_memory()
        memory['system_knowledge'] = {}
        save_memory(memory)
        
        # 7. Execute Task directly (synchronously)
        orch.state["goal"] = "Test the chronicler integration"
        # Skip the planning check and run the task flow
        result = orch._start_task()
        
        print(f"Orchestration result: {result}")
        
        # 8. Verify Chronicler was called
        mock_extract.assert_called_once()
        
        # 9. Verify UI was notified
        mock_ui.write_log.assert_any_call("SYS: Chronicler saved 2 technical facts.")
        
        # 10. Verify Memory was updated
        final_memory = load_memory()
        facts = final_memory.get('system_knowledge', {})
        print(f"Stored facts: {facts}")
        
        self.assertEqual(len(facts), 2)
        self.assertIn("tech_stack", facts)
        self.assertIn("naming_convention", facts)
        
        print("Integration test PASSED!")

if __name__ == "__main__":
    unittest.main()

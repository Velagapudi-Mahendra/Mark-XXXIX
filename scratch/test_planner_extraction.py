
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from agent.planner import extract_technical_details

class TestPlannerExtraction(unittest.TestCase):
    
    @patch("core.llm_provider.generate_text")
    def test_extract_technical_details(self, mock_generate):
        # Setup mock response
        mock_response = """
        ```json
        {
            "tech_stack": "Python 3.12, PyQt6",
            "naming_convention": "SnakeCase for functions"
        }
        ```
        """
        mock_generate.return_value = mock_response
        
        goal = "Implement a new UI feature"
        steps = [
            {"step": 1, "tool": "file_processor", "description": "Read ui.py"},
            {"step": 2, "tool": "code_helper", "description": "Add new widget"}
        ]
        results = {
            "1": "File content shows PyQt6 imports.",
            "2": "Successfully added NewWidget class."
        }
        
        extracted = extract_technical_details(goal, steps, results)
        
        print(f"Extracted: {extracted}")
        
        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted["tech_stack"], "Python 3.12, PyQt6")
        self.assertEqual(extracted["naming_convention"], "SnakeCase for functions")
        
        # Verify force_nvidia was used
        mock_generate.assert_called_once()
        args, kwargs = mock_generate.call_args
        self.assertTrue(kwargs.get("force_nvidia"))

if __name__ == "__main__":
    unittest.main()

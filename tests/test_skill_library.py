import unittest
import json
import os
import tempfile
from pathlib import Path

from core.skill_manager import SkillManager

class TestSkillLibrary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.temp_dir.name)
        self.skills_dir = self.workspace_path / "Skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy skill
        self.dummy_skill = {
            "name": "test_skill",
            "description": "A test skill.",
            "parameters": ["var1", "var2"],
            "steps": [
                {
                    "step": 1,
                    "tool": "echo",
                    "description": "Echo variables",
                    "args": {
                        "text": "{{var1}} and {{var2}}"
                    }
                }
            ]
        }
        
        skill_path = self.skills_dir / "test_skill.json"
        with open(skill_path, "w", encoding="utf-8") as f:
            json.dump(self.dummy_skill, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_skills(self):
        manager = SkillManager(self.workspace_path)
        skills = manager.list_skills()
        
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0]["name"], "test_skill")
        self.assertEqual(manager.get_skill("test_skill")["name"], "test_skill")

    def test_parameter_substitution(self):
        manager = SkillManager(self.workspace_path)
        params = {"var1": "Hello", "var2": "World"}
        resolved = manager.resolve_placeholders("test_skill", params)
        
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["steps"][0]["args"]["text"], "Hello and World")

    def test_reload_skills(self):
        manager = SkillManager(self.workspace_path)
        self.assertEqual(len(manager.list_skills()), 1)
        
        # Add new skill
        new_skill = {
            "name": "new_skill",
            "description": "New",
            "parameters": [],
            "steps": [] # Should fail validation due to empty steps but wait, manager just checks if "steps" in skill
        }
        with open(self.skills_dir / "new_skill.json", "w", encoding="utf-8") as f:
            json.dump(new_skill, f)
            
        manager.reload_skills()
        self.assertEqual(len(manager.list_skills()), 2)

    def test_invalid_skill(self):
        # Create invalid skill (name mismatch)
        invalid_skill = {
            "name": "wrong_name",
            "description": "Invalid",
            "steps": []
        }
        with open(self.skills_dir / "invalid_skill.json", "w", encoding="utf-8") as f:
            json.dump(invalid_skill, f)
            
        manager = SkillManager(self.workspace_path)
        self.assertIsNone(manager.get_skill("invalid_skill"))
        self.assertIsNone(manager.get_skill("wrong_name"))

if __name__ == "__main__":
    unittest.main()

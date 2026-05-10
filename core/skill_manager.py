
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

class SkillManager:
    """
    Manages JARVIS Skills - pre-defined multi-step workflows stored as JSON.
    Skills are stored in <workspace>/Skills/ and loaded into memory at startup.
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.skills_dir = workspace_path / "Skills"
        self.skills: Dict[str, Any] = {}
        
        # Ensure directory exists
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.reload_skills()

    def reload_skills(self) -> int:
        """Scans the Skills directory and loads all valid skill JSONs."""
        self.skills = {}
        if not self.skills_dir.exists():
            return 0
            
        count = 0
        for file in self.skills_dir.glob("*.json"):
            try:
                skill_data = json.loads(file.read_text(encoding="utf-8"))
                skill_name = file.stem
                
                # Validation: Name inside JSON must match filename
                if skill_data.get("name") != skill_name:
                    print(f"[SkillManager] ⚠️ Validation failed for {file.name}: Name mismatch.")
                    continue
                
                # Validation: Must have steps
                if "steps" not in skill_data or not isinstance(skill_data["steps"], list):
                    print(f"[SkillManager] ⚠️ Validation failed for {file.name}: No steps found.")
                    continue
                    
                self.skills[skill_name] = skill_data
                count += 1
            except Exception as e:
                print(f"[SkillManager] ❌ Error loading {file.name}: {e}")
                
        print(f"[SkillManager] Loaded {count} skills from {self.skills_dir}")
        return count

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict[str, str]]:
        """Returns a list of available skills with descriptions."""
        return [
            {"name": name, "description": data.get("description", "No description")}
            for name, data in self.skills.items()
        ]

    def resolve_placeholders(self, skill_name: str, user_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Performs the first-pass substitution: replacing {{param}} with user-provided values.
        Returns a modified skill structure ready for the Orchestrator.
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return None
            
        # Create a deep-ish copy (we only care about the steps/args)
        skill_str = json.dumps(skill)
        
        # Replace {{param}} with user_params
        for key, value in user_params.items():
            placeholder = f"{{{{{key}}}}}"
            skill_str = skill_str.replace(placeholder, str(value))
            
        return json.loads(skill_str)

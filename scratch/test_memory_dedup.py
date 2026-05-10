
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from memory.memory_manager import remember, load_memory, save_memory

def test_deduplication():
    # Setup: Ensure system_knowledge is empty for the test
    memory = load_memory()
    memory['system_knowledge'] = {}
    save_memory(memory)
    
    print("Testing deduplication...")
    
    # Fact 1: Original
    res1 = remember("python_version", "Python 3.12.0", category="system_knowledge")
    print(f"1: {res1}")
    
    # Fact 2: Duplicate (normalized should match)
    res2 = remember("python_version_v2", "python 3.12", category="system_knowledge")
    print(f"2: {res2}")
    
    # Fact 3: New fact
    res3 = remember("ui_framework", "Using PyQt6 for UI", category="system_knowledge")
    print(f"3: {res3}")
    
    # Fact 4: Duplicate (case normalized)
    res4 = remember("ui_fw_alias", "using pyqt6 for ui", category="system_knowledge")
    print(f"4: {res4}")
    
    final_memory = load_memory()
    facts = final_memory.get('system_knowledge', {})
    print(f"Stored facts in system_knowledge: {json.dumps(facts, indent=2)}")
    
    # Expectations:
    # "python_version" (Python 3.12.0)
    # "ui_framework" (Using PyQt6 for UI)
    # The others should have been rejected by the normalization check in remember()
    
    # Actually, look at the logic in remember():
    # if category == "system_knowledge":
    #     norm_new = _normalize_fact(value)
    #     for k, v in cat_data.items():
    #         if _normalize_fact(v.get("value", "")) == norm_new:
    #             return f"Fact already known (normalized): {category}/{k}"
    
    assert len(facts) == 2, f"Expected 2 facts, got {len(facts)}"
    assert "python_version" in facts
    assert "ui_framework" in facts
    assert "python_version_v2" not in facts
    assert "ui_fw_alias" not in facts
    
    print("Deduplication test PASSED!")

if __name__ == "__main__":
    test_deduplication()

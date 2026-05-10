
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

print("Checking imports...")
try:
    import main
    print("main.py imported successfully!")
    
    from ui import JarvisUI
    print("ui.py imported successfully!")
    
    from core.orchestrator import AgentOrchestrator
    print("orchestrator.py imported successfully!")
    
    from memory.memory_manager import remember
    print("memory_manager.py imported successfully!")
    
    print("\nALL IMPORTS OK. The system is structurally sound.")
except Exception as e:
    print(f"\nIMPORT FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

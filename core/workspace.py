import os
import json
from pathlib import Path

# WORKSPACE
WORKSPACE_PATH = None

def init_workspace(config_path: Path):
    global WORKSPACE_PATH
    
    # Default path
    default_workspace = Path.home() / "JARVIS_Workspace"
    
    # Load config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        config = {}

    workspace_path_str = config.get("workspace_path")
    if workspace_path_str:
        WORKSPACE_PATH = Path(workspace_path_str)
    else:
        WORKSPACE_PATH = default_workspace
        # Save back to config if it was missing
        config["workspace_path"] = str(WORKSPACE_PATH)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    # Create directory and subdirectories
    subdirs = ["Research", "Code", "Images", "Downloads", "Outputs", "Archive"]
    WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
    for sd in subdirs:
        (WORKSPACE_PATH / sd).mkdir(parents=True, exist_ok=True)

    print(f"[Workspace] Initialized at: {WORKSPACE_PATH}")
    return WORKSPACE_PATH

def get_workspace_path():
    global WORKSPACE_PATH
    if WORKSPACE_PATH is None:
        # Fallback if not initialized (though it should be)
        return Path.home() / "JARVIS_Workspace"
    return WORKSPACE_PATH

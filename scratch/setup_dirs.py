import os
from pathlib import Path

def setup_project():
    # Create state directory
    os.makedirs("state", exist_ok=True)
    
    # Update .gitignore
    gitignore = Path(".gitignore")
    content = ""
    if gitignore.exists():
        content = gitignore.read_text()
    
    if "state/" not in content:
        with open(".gitignore", "a") as f:
            f.write("\nstate/\n")
        print("Added state/ to .gitignore")
    else:
        print("state/ already in .gitignore")

if __name__ == "__main__":
    setup_project()

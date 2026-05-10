import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class ContextManager:
    """
    Manages short-term session state, active references, and memory injection.
    """
    def __init__(self, memory_manager):
        self.memory_manager = memory_manager
        self.session_history: List[Dict[str, Any]] = []
        self.active_references: Dict[str, Dict[str, Any]] = {} # path -> {timestamp, type}
        self.max_history = 10
        self.reference_ttl = 300 # 5 minutes

    def get_workspace_path(self):
        """Returns the current workspace root path."""
        from core.workspace import get_workspace_path
        return get_workspace_path()

    def add_message(self, role: str, content: str, tool_results: Optional[List[Any]] = None):
        """Adds a message to the session history."""
        self.session_history.append({
            "role": role,
            "content": content,
            "results": tool_results,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.session_history) > self.max_history:
            self.session_history.pop(0)

    def add_reference(self, ref_path: str, ref_type: str = "file"):
        """Adds or updates an active reference."""
        self.active_references[ref_path] = {
            "type": ref_type,
            "timestamp": time.time()
        }

    def _cleanup_references(self):
        """Removes expired references."""
        now = time.time()
        expired = [path for path, data in self.active_references.items() 
                   if now - data["timestamp"] > self.reference_ttl]
        for path in expired:
            del self.active_references[path]

    def clear_context(self):
        """Resets the context."""
        self.session_history = []
        self.active_references = {}
        print("[Context] Context cleared.")

    def get_context_summary(self) -> str:
        """Returns a string summary of the current session context."""
        self._cleanup_references()
        
        summary = []
        if self.active_references:
            summary.append("[ACTIVE REFERENCES]")
            for path, data in self.active_references.items():
                summary.append(f"- {data['type']}: {path}")
            summary.append("")

        if self.session_history:
            summary.append("[RECENT SESSION ACTIVITY]")
            for msg in self.session_history:
                summary.append(f"{msg['role'].upper()}: {msg['content']}")
                if msg.get("results"):
                    summary.append(f"RESULT: {msg['results']}")
            summary.append("")
            
        return "\n".join(summary)

    def inject_context(self, prompt_template: str, query: str = "") -> str:
        """
        Fills placeholders in the prompt template with dynamic context.
        Placeholders: {{SESSION_HISTORY}}, {{RELEVANT_MEMORIES}}, {{ACTIVE_REFERENCES}}
        """
        from memory.retriever import get_relevant_memories
        
        # Get relevant memories
        memory_data = self.memory_manager.load_memory()
        relevant = get_relevant_memories(query or (self.session_history[-1]['content'] if self.session_history else ""), memory_data)
        
        mem_str = "[RELEVANT MEMORIES]\n" + "\n".join([f"- {m['key']}: {m['value']}" for m in relevant]) if relevant else ""
        
        # Get session history
        history_str = self.get_context_summary()
        
        # Replace placeholders
        final_prompt = prompt_template.replace("{{SESSION_HISTORY}}", history_str)
        final_prompt = final_prompt.replace("{{RELEVANT_MEMORIES}}", mem_str)
        final_prompt = final_prompt.replace("{{WORKSPACE_PATH}}", str(self.get_workspace_path()))
        
        return final_prompt

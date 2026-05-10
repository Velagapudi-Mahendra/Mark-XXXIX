import time
import threading
import json
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from pathlib import Path

class ProactivityEngine(threading.Thread):
    """
    Background thread that analyzes user habits and suggests/performs proactive actions.
    """
    def __init__(self, memory_manager, ui, orchestrator, trust_level: str = "suggest"):
        super().__init__(daemon=True, name="ProactivityEngine")
        self.memory_manager = memory_manager
        self.ui = ui
        self.orchestrator = orchestrator
        self.trust_level = trust_level # off, suggest, auto
        self.running = True
        self.stop_event = threading.Event()
        self.learning_threshold = 3
        self.check_interval = 300 # 5 minutes

    def stop(self):
        self.running = False
        self.stop_event.set()

    def run(self):
        print(f"[Proactivity] Engine started. Trust Level: {self.trust_level}")
        while self.running:
            if self.trust_level != "off":
                self._analyze_habits()
            # Wait for interval or stop event
            self.stop_event.wait(self.check_interval)

    def _analyze_habits(self):
        """
        Analyzes the 'habits' category in memory for patterns.
        """
        memory = self.memory_manager.load_memory()
        habits = memory.get("habits", {})
        
        if not habits:
            return

        now = datetime.now()
        current_hour = now.hour
        
        for action_key, data in habits.items():
            if not isinstance(data, dict): continue
            
            # Extract count from potentially wrapped value
            raw_val = data.get(str(current_hour), 0)
            if isinstance(raw_val, dict) and "value" in raw_val:
                try:
                    count = int(float(raw_val["value"]))
                except (ValueError, TypeError):
                    count = 0
            else:
                try:
                    count = int(raw_val)
                except (ValueError, TypeError):
                    count = 0
            
            if count >= self.learning_threshold:
                self._handle_pattern(action_key, current_hour)

    def _handle_pattern(self, action: str, hour: int):
        """
        Handles a detected pattern based on trust level.
        """
        action_desc = action.replace("_", " ")
        msg = f"Sir, I noticed you usually {action_desc} around this time."
        
        if self.trust_level == "suggest":
            self.ui.show_suggestion(f"Should I {action_desc}?", lambda: self._execute_action(action))
        
        elif self.trust_level == "auto":
            # Check confirmation count (stored in habits under 'confirmations')
            memory = self.memory_manager.load_memory()
            habit_data = memory.get("habits", {}).get(action, {})
            
            raw_conf = habit_data.get("confirmations", 0)
            if isinstance(raw_conf, dict) and "value" in raw_conf:
                try:
                    confirmations = int(float(raw_conf["value"]))
                except (ValueError, TypeError):
                    confirmations = 0
            else:
                try:
                    confirmations = int(raw_conf)
                except (ValueError, TypeError):
                    confirmations = 0
            
            if confirmations < self.learning_threshold:
                self.ui.show_suggestion(f"Execute {action_desc}?", lambda: self._confirm_and_execute(action))
            else:
                # Autonomous execution
                print(f"[Proactivity] Autonomous execution: {action}")
                self.ui.write_log(f"PROACTIVE: Executing habit '{action_desc}'")
                self._execute_action(action)

    def _confirm_and_execute(self, action: str):
        # Update confirmation count
        memory = self.memory_manager.load_memory()
        habits = memory.get("habits", {})
        if action not in habits: habits[action] = {}
        
        raw_conf = habits[action].get("confirmations", 0)
        if isinstance(raw_conf, dict) and "value" in raw_conf:
            try:
                count = int(float(raw_conf["value"]))
            except (ValueError, TypeError):
                count = 0
        else:
            try:
                count = int(raw_conf)
            except (ValueError, TypeError):
                count = 0
                
        habits[action]["confirmations"] = count + 1
        self.memory_manager.update_memory({"habits": habits})
        
        self._execute_action(action)

    def _execute_action(self, action: str):
        # Route through orchestrator or direct tool call
        self.orchestrator.execute(action)

    def log_action(self, action_key: str):
        """
        Called by main.py to log a user action.
        """
        now = datetime.now()
        hour = str(now.hour)
        
        memory = self.memory_manager.load_memory()
        habits = memory.get("habits", {})
        
        if action_key not in habits:
            habits[action_key] = {}
        
        raw_val = habits[action_key].get(hour, 0)
        # Handle MemoryManager wrapper
        if isinstance(raw_val, dict) and "value" in raw_val:
            try:
                count = int(float(raw_val["value"]))
            except (ValueError, TypeError):
                count = 0
        else:
            try:
                count = int(raw_val)
            except (ValueError, TypeError):
                count = 0

        habits[action_key][hour] = count + 1
        self.memory_manager.update_memory({"habits": habits})

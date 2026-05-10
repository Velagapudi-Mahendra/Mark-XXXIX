import os
import platform
import base64
import cv2
import numpy as np
from typing import Optional, List, Dict, Any
from pathlib import Path

class MultimodalFusion:
    """
    Fuses text, vision, and audio context into a single Gemini request.
    Handles OS-level window focus for ambiguity resolution.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._os = platform.system()

    def get_focused_window_info(self) -> str:
        """
        Retrieves the title of the currently focused window.
        """
        try:
            if self._os == "Windows":
                import win32gui
                window = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(window)
                return f"Currently focused window: '{title}'"
            elif self._os == "Darwin":
                # Placeholder for Quartz
                return "Focused window info not yet available on macOS."
            elif self._os == "Linux":
                # Placeholder for xdotool
                return "Focused window info not yet available on Linux."
        except Exception as e:
            return f"Could not determine focused window: {e}"
        return "Unknown focused window."

    def capture_webcam(self) -> Optional[bytes]:
        """
        Captures a single frame from the webcam.
        """
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return None
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return None
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer.tobytes()
        except Exception as e:
            print(f"[Fusion] Webcam capture failed: {e}")
            return None

    def process_multimodal(self, text: str, image_path: Optional[str] = None, audio_path: Optional[str] = None, include_webcam: bool = False) -> str:
        """
        Sends fused context to Gemini and returns the response.
        """
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")

        # Build message parts
        parts = []
        
        # 1. Add focused window context
        focus_info = self.get_focused_window_info()
        parts.append(f"SYSTEM CONTEXT: {focus_info}\n")
        
        # 2. Add text prompt
        parts.append(f"USER REQUEST: {text}\n")
        
        # 3. Add image if available
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_data = f.read()
            parts.append({
                "mime_type": "image/png",
                "data": img_data
            })
            
        # 4. Add audio if available (as data part)
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            parts.append({
                "mime_type": "audio/wav",
                "data": audio_data
            })
            
        # 5. Add webcam if requested
        if include_webcam:
            webcam_data = self.capture_webcam()
            if webcam_data:
                parts.append({
                    "mime_type": "image/jpeg",
                    "data": webcam_data
                })

        try:
            response = model.generate_content(parts)
            return response.text.strip()
        except Exception as e:
            return f"Multimodal fusion error: {e}"

    def resolve_ambiguity(self, options: List[str]) -> str:
        """
        Called when multiple targets are found. Returns a question for the user.
        """
        return f"Sir, I see multiple targets: {', '.join(options)}. Which one did you mean?"

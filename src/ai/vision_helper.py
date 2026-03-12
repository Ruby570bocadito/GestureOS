import base64
import io
from typing import Optional, List, Dict
from pathlib import Path

import ollama
from PIL import Image

from src.core.config import OLLAMA_VISION_MODEL, SCREENSHOT_DIR


class VisionHelper:
    def __init__(
        self,
        model: str = OLLAMA_VISION_MODEL,
        screenshot_dir: Path = SCREENSHOT_DIR
    ):
        self.model = model
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def capture_screen(self, region: Optional[tuple] = None) -> Image.Image:
        import mss
        import numpy as np

        with mss.mss() as sct:
            if region:
                monitor = {
                    "left": region[0],
                    "top": region[1],
                    "width": region[2],
                    "height": region[3]
                }
            else:
                monitor = sct.monitors[1]

            screenshot = sct.grab(monitor)

            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img = img.resize((img.width // 2, img.height // 2))

            return img

    def save_screenshot(self, filename: str = "screenshot.png") -> Path:
        img = self.capture_screen()
        filepath = self.screenshot_dir / filename
        img.save(filepath)
        return filepath

    def analyze_screen(self, prompt: str = "Describe lo que ves en la pantalla") -> str:
        try:
            img = self.capture_screen()

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            with open("temp_screenshot.png", "wb") as f:
                f.write(img_bytes.getvalue())

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": ["temp_screenshot.png"]
                    }
                ],
                options={
                    "temperature": 0.3,
                    "num_predict": 300
                }
            )

            import os
            if os.path.exists("temp_screenshot.png"):
                os.remove("temp_screenshot.png")

            return response['message']['content']

        except Exception as e:
            return f"Error al analizar pantalla: {str(e)}"

    def find_element(self, description: str) -> Optional[Dict]:
        prompt = f"""Analiza esta captura de pantalla y encuentra el elemento que coincida con: '{description}'
        
Proporciona la posición aproximada en formato JSON:
{{
    "found": true/false,
    "position": {{"x": valor, "y": valor, "width": valor, "height": valor}},
    "description": "descripción del elemento encontrado"
}}"""

        try:
            img = self.capture_screen()

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            with open("temp_screenshot.png", "wb") as f:
                f.write(img_bytes.getvalue())

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": ["temp_screenshot.png"]
                    }
                ],
                options={
                    "temperature": 0.1,
                    "num_predict": 200
                }
            )

            import os
            if os.path.exists("temp_screenshot.png"):
                os.remove("temp_screenshot.png")

            content = response['message']['content']

            import json
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                return json.loads(content[start:end].strip())
            elif "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                return json.loads(content[start:end])

        except Exception as e:
            return {"found": False, "error": str(e)}

        return {"found": False}

    def get_screen_context(self) -> Dict:
        try:
            img = self.capture_screen()

            width, height = img.size

            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

            with open("temp_screenshot.png", "wb") as f:
                f.write(img_bytes.getvalue())

            prompt = """Analiza brevemente esta pantalla. Proporciona:
1. ¿Qué aplicación está activa?
2. ¿Hay alguna ventana visible?
3. ¿Hay algún botón o elemento interactivo destacado?

Responde de forma muy concisa."""

            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": ["temp_screenshot.png"]
                    }
                ],
                options={
                    "temperature": 0.3,
                    "num_predict": 150
                }
            )

            import os
            if os.path.exists("temp_screenshot.png"):
                os.remove("temp_screenshot.png")

            return {
                "width": width,
                "height": height,
                "context": response['message']['content']
            }

        except Exception as e:
            return {
                "width": 0,
                "height": 0,
                "context": f"Error: {str(e)}"
            }

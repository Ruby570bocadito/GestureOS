import base64
import io
import os
import logging
import tempfile
from typing import Optional, List, Dict
from pathlib import Path

import ollama
from PIL import Image

from src.core.config import (
    OLLAMA_VISION_MODEL, SCREENSHOT_DIR,
    VISION_RESIZE_FACTOR, OLLAMA_TEMPERATURE,
    OLLAMA_NUM_PREDICT, OLLAMA_VISION_NUM_PREDICT,
)

logger = logging.getLogger("handscontrol.vision_helper")


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
            img = img.resize((img.width // VISION_RESIZE_FACTOR, img.height // VISION_RESIZE_FACTOR))
            return img

    def save_screenshot(self, filename: str = "screenshot.png") -> Path:
        img = self.capture_screen()
        filepath = self.screenshot_dir / filename
        img.save(filepath)
        return filepath

    def _send_vision_request(self, img: Image.Image, prompt: str, num_predict: int) -> str:
        """Send a vision request to Ollama using a temporary file."""
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')

        fd, tmp_path = tempfile.mkstemp(suffix=".png", prefix="handscontrol_vision_")
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(img_bytes.getvalue())

            response = ollama.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [tmp_path]
                }],
                options={
                    "temperature": OLLAMA_TEMPERATURE,
                    "num_predict": num_predict
                }
            )
            return response['message']['content']
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def analyze_screen(self, prompt: str = "Describe lo que ves en la pantalla") -> str:
        try:
            img = self.capture_screen()
            return self._send_vision_request(img, prompt, OLLAMA_VISION_NUM_PREDICT)
        except Exception as e:
            logger.error(f"Screen analysis failed: {e}")
            return f"Error al analizar pantalla: {str(e)}"

    def find_element(self, description: str) -> Optional[Dict]:
        prompt = (
            f"Analiza esta captura de pantalla y encuentra el elemento que coincida con: '{description}'\n\n"
            "Proporciona la posicion aproximada en formato JSON:\n"
            '{"found": true/false, "position": {"x": valor, "y": valor, "width": valor, "height": valor}, '
            '"description": "descripcion del elemento encontrado"}'
        )

        try:
            img = self.capture_screen()
            content = self._send_vision_request(img, prompt, 200)

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
            logger.error(f"Element search failed: {e}")
            return {"found": False, "error": str(e)}

        return {"found": False}

    def get_screen_context(self) -> Dict:
        prompt = (
            "Analiza brevemente esta pantalla. Proporciona:\n"
            "1. Que aplicacion esta activa?\n"
            "2. Hay alguna ventana visible?\n"
            "3. Hay algun boton o elemento interactivo destacado?\n\n"
            "Responde de forma muy concisa."
        )

        try:
            img = self.capture_screen()
            width, height = img.size
            context = self._send_vision_request(img, prompt, 150)

            return {
                "width": width,
                "height": height,
                "context": context
            }
        except Exception as e:
            logger.error(f"Screen context failed: {e}")
            return {
                "width": 0,
                "height": 0,
                "context": f"Error: {str(e)}"
            }

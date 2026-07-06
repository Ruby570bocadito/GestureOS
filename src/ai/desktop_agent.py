import json
import base64
import threading
import queue
import time
import logging
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

import ollama

from src.core.config import (
    OLLAMA_MODEL, OLLAMA_VISION_MODEL, OLLAMA_BASE_URL,
    OLLAMA_TEMPERATURE, OLLAMA_NUM_PREDICT, OLLAMA_ASK_TIMEOUT,
    MAX_CONVERSATION_LENGTH,
)

logger = logging.getLogger("handscontrol.desktop_agent")


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    ERROR = "error"


@dataclass
class Message:
    role: str
    content: str
    images: Optional[List[str]] = None


@dataclass
class Action:
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


class DesktopAgent:
    def __init__(
        self,
        model: str = OLLAMA_MODEL,
        vision_model: str = OLLAMA_VISION_MODEL,
        base_url: str = OLLAMA_BASE_URL
    ):
        self.model = model
        self.vision_model = vision_model
        self.base_url = base_url

        self.state = AgentState.IDLE
        self._is_active = False

        self._conversation: List[Message] = []
        self._max_conversation_length = MAX_CONVERSATION_LENGTH

        self._request_queue: queue.Queue = queue.Queue()
        self._response_queue: queue.Queue = queue.Queue()

        self._processing_thread: Optional[threading.Thread] = None

        self._on_state_change_callback: Optional[Callable[[AgentState], None]] = None
        self._on_action_callback: Optional[Callable[[Action], None]] = None

        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """Eres HandsControl, un asistente de escritorio con control por gestos.

Capacidades disponibles:
1. Control de mouse: click, right_click, double_click, drag
2. Control de teclado: write, press_key, hotkey
3. Gestion de ventanas: minimize, maximize, close, switch_window
4. Sistema: screenshot, open_app, volume_up, volume_down
5. Busqueda: search_web, search_files

Cuando el usuario solicite una accion, responde en JSON con:
{
    "action": "tipo_de_accion",
    "params": {"param1": "valor1"},
    "explanation": "explicacion breve"
}

Si no necesitas ejecutar acciones, responde:
{
    "action": "respond",
    "params": {"text": "tu respuesta"},
    "explanation": "explicacion"
}

Ejemplos de comandos:
- "Abre el navegador" -> {"action": "open_app", "params": {"app": "browser"}, "explanation": "Abriendo navegador"}
- "Cierra esta ventana" -> {"action": "close", "params": {}, "explanation": "Cerrando ventana"}
- "Que hay en mi pantalla?" -> {"action": "analyze_screen", "params": {}, "explanation": "Analizando pantalla"}

Responde siempre en espanol de forma clara y concisa."""

    def start(self):
        if self._is_active:
            return

        self._is_active = True

        self._conversation.append(Message(
            role="system",
            content=self._system_prompt
        ))

        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self._processing_thread.start()

    def stop(self):
        self._is_active = False
        if self._processing_thread:
            self._processing_thread.join(timeout=2)

    def _processing_loop(self):
        while self._is_active:
            try:
                request = self._request_queue.get(timeout=1)
            except queue.Empty:
                continue

            self._set_state(AgentState.THINKING)

            try:
                response = self._process_request(request)
                self._response_queue.put(response)

            except Exception as e:
                logger.error(f"Request processing error: {e}")
                self._set_state(AgentState.ERROR)
                error_response = {
                    "action": "error",
                    "params": {"message": str(e)},
                    "explanation": f"Error: {str(e)}"
                }
                self._response_queue.put(error_response)

    def _process_request(self, request: Dict) -> Dict:
        user_message = request.get("message", "")
        images = request.get("images")
        callback = request.get("callback")

        self._conversation.append(Message(
            role="user",
            content=user_message,
            images=images
        ))

        if len(self._conversation) > self._max_conversation_length:
            self._conversation = [self._conversation[0]] + self._conversation[-self._max_conversation_length:]

        try:
            model = self.vision_model if images else self.model
            response = ollama.chat(
                model=model,
                messages=self._convert_conversation(),
                options={
                    "temperature": OLLAMA_TEMPERATURE,
                    "num_predict": OLLAMA_VISION_NUM_PREDICT if images else OLLAMA_NUM_PREDICT
                }
            )

            assistant_message = response['message']['content']
            self._conversation.append(Message(
                role="assistant",
                content=assistant_message
            ))

            parsed = self._parse_response(assistant_message)

            if parsed.get("action"):
                self._set_state(AgentState.EXECUTING)
                action = Action(
                    action_type=parsed.get("action", "respond"),
                    params=parsed.get("params", {}),
                    description=parsed.get("explanation", "")
                )

                if self._on_action_callback:
                    self._on_action_callback(action)

            if callback:
                try:
                    callback(parsed)
                except Exception as e:
                    logger.error(f"Async callback failed: {e}")

            self._set_state(AgentState.IDLE)
            return parsed

        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            self._set_state(AgentState.ERROR)
            return {
                "action": "error",
                "params": {"message": str(e)},
                "explanation": f"Error al procesar: {str(e)}"
            }

    def _convert_conversation(self) -> List[Dict]:
        conv = []
        for msg in self._conversation:
            msg_dict = {
                "role": msg.role,
                "content": msg.content
            }
            if msg.images:
                msg_dict["images"] = msg.images
            conv.append(msg_dict)
        return conv

    def _parse_response(self, response: str) -> Dict:
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end == -1:
                    end = len(response)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end == -1:
                    end = len(response)
                json_str = response[start:end].strip()
            else:
                json_str = response

            return json.loads(json_str)

        except json.JSONDecodeError:
            return {
                "action": "respond",
                "params": {"text": response},
                "explanation": "Respondiendo al usuario"
            }

    def ask(self, question: str, images: Optional[List[str]] = None) -> Dict:
        if not self._is_active:
            self.start()

        request = {
            "message": question,
            "images": images
        }

        self._request_queue.put(request)

        try:
            response = self._response_queue.get(timeout=OLLAMA_ASK_TIMEOUT)
            return response
        except queue.Empty:
            return {
                "action": "error",
                "params": {"message": "Timeout"},
                "explanation": "La solicitud tardo demasiado"
            }

    def ask_async(self, question: str, callback: Optional[Callable[[Dict], None]] = None):
        request = {
            "message": question,
            "callback": callback
        }
        self._request_queue.put(request)

    def get_response(self) -> Optional[Dict]:
        try:
            return self._response_queue.get_nowait()
        except queue.Empty:
            return None

    def clear_conversation(self):
        self._conversation = [Message(
            role="system",
            content=self._system_prompt
        )]

    def _set_state(self, state: AgentState):
        self.state = state
        if self._on_state_change_callback:
            try:
                self._on_state_change_callback(state)
            except Exception as e:
                logger.error(f"Agent state change callback failed: {e}")

    def on_state_change(self, callback: Callable[[AgentState], None]):
        self._on_state_change_callback = callback

    def on_action(self, callback: Callable[[Action], None]):
        self._on_action_callback = callback

    def get_state(self) -> AgentState:
        return self.state

    def get_conversation_length(self) -> int:
        return len(self._conversation)

    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt
        if self._conversation and self._conversation[0].role == "system":
            self._conversation[0].content = prompt
        else:
            self._conversation.insert(0, Message(role="system", content=prompt))

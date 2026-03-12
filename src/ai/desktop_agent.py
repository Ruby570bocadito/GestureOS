import json
import base64
import threading
import queue
import time
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

import ollama

from src.core.config import OLLAMA_MODEL, OLLAMA_VISION_MODEL, OLLAMA_BASE_URL


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
        self._max_conversation_length = 50

        self._request_queue: queue.Queue = queue.Queue()
        self._response_queue: queue.Queue = queue.Queue()

        self._processing_thread: Optional[threading.Thread] = None

        self._on_state_change_callback: Optional[Callable[[AgentState], None]] = None
        self._on_action_callback: Optional[Callable[[Action], None]] = None

        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return """Eres GestureOS, un asistente de escritorio con control por gestos.

Capacidades disponibles:
1. Control de mouse: click, right_click, double_click, drag
2. Control de teclado: write, press_key, hotkey
3. Gestión de ventanas: minimize, maximize, close, switch_window
4. Sistema: screenshot, open_app, volume_up, volume_down
5. Búsqueda: search_web, search_files

Cuando el usuario solicite una acción, responde en JSON con:
{
    "action": "tipo_de_accion",
    "params": {"param1": "valor1"},
    "explanation": "explicación breve"
}

Si no necesitas ejecutar acciones, responde:
{
    "action": "respond",
    "params": {"text": "tu respuesta"},
    "explanation": "explicación"
}

Ejemplos de comandos:
- "Abre el navegador" -> {"action": "open_app", "params": {"app": "browser"}, "explanation": "Abriendo navegador"}
- "Cierra esta ventana" -> {"action": "close", "params": {}, "explanation": "Cerrando ventana"}
- "¿Qué hay en mi pantalla?" -> {"action": "analyze_screen", "params": {}, "explanation": "Analizando pantalla"}

Responde siempre en español de forma clara y concisa."""

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
                self._set_state(AgentState.ERROR)
                error_response = {
                    "action": "error",
                    "params": {"message": str(e)},
                    "explanation": f"Error: {str(e)}"
                }
                self._response_queue.put(error_response)

    def _process_request(self, request: Dict) -> Dict:
        user_message = request.get("message", "")
        images = request.get("images", None)

        self._conversation.append(Message(
            role="user",
            content=user_message,
            images=images
        ))

        if len(self._conversation) > self._max_conversation_length:
            self._conversation = [self._conversation[0]] + self._conversation[-self._max_conversation_length:]

        try:
            if images:
                response = ollama.chat(
                    model=self.vision_model,
                    messages=self._convert_conversation(),
                    options={
                        "temperature": 0.3,
                        "num_predict": 500
                    }
                )
            else:
                response = ollama.chat(
                    model=self.model,
                    messages=self._convert_conversation(),
                    options={
                        "temperature": 0.3,
                        "num_predict": 500
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

            self._set_state(AgentState.IDLE)
            return parsed

        except Exception as e:
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
            response = self._response_queue.get(timeout=30)
            return response
        except queue.Empty:
            return {
                "action": "error",
                "params": {"message": "Timeout"},
                "explanation": "La solicitud tardó demasiado"
            }

    def ask_async(self, question: str, callback: Callable[[Dict], None] = None):
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
            self._on_state_change_callback(state)

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

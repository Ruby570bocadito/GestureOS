"""
VoiceAssistant — GestureOS
==========================
Sistema de control por voz en español. Escucha continuamente, reconoce
comandos predefinidos y los despacha con callbacks de acción.

Comandos disponibles (ejemplos):
  "abrir navegador"   → open_app: browser
  "cerrar ventana"    → close_window
  "copiar"            → hotkey: ctrl+c
  "pegar"             → hotkey: ctrl+v
  "deshacer"          → hotkey: ctrl+z
  "captura"           → screenshot
  "subir volumen"     → volume_up
  "bajar volumen"     → volume_down
  "activar teclado"   → toggle_keyboard
  "apagar voz"        → stop_voice
  "agente [texto]"    → send to AI agent
"""
import threading
import queue
import time
import re
from typing import Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

import speech_recognition as sr
import pyttsx3

from src.core.config import VOICE_LANGUAGE, VOICE_RATE, VOICE_VOLUME


class VoiceState(Enum):
    IDLE       = "idle"
    LISTENING  = "listening"
    PROCESSING = "processing"
    SPEAKING   = "speaking"
    ERROR      = "error"


@dataclass
class VoiceCommand:
    command: str        # raw text
    action: str         # matched action key
    params: dict        # extra params extracted
    confidence: float
    timestamp: float


# ────────────────────────────────────────────────────────────────────────────
# Command patterns
# ────────────────────────────────────────────────────────────────────────────
_ART = r"(?:el |la |un |una |los |las )?"   # optional Spanish article


def _mk(pattern: str, action: str, params: dict = None):
    return (re.compile(pattern, re.IGNORECASE), action, params or {})


COMMAND_PATTERNS: List[Tuple] = [
    # Mouse & clicks
    _mk(r"(click|clic|hacer click)", "click_left"),
    _mk(r"(click derecho|clic derecho|boton derecho)", "click_right"),
    _mk(r"(doble click|doble clic)", "double_click"),

    # Teclado virtual
    _mk(r"(activar|abrir|mostrar) " + _ART + r"teclado", "toggle_keyboard"),
    _mk(r"(desactivar|cerrar|ocultar) " + _ART + r"teclado", "toggle_keyboard"),

    # Apps
    _mk(r"(abrir|abre) " + _ART + r"navegador", "open_app", {"app": "browser"}),
    _mk(r"(abrir|abre) " + _ART + r"(chrome|chromium)", "open_app", {"app": "chrome"}),
    _mk(r"(abrir|abre) " + _ART + r"(firefox|mozilla)", "open_app", {"app": "firefox"}),
    _mk(r"(abrir|abre) " + _ART + r"(bloc de notas|notepad)", "open_app", {"app": "notepad"}),
    _mk(r"(abrir|abre) " + _ART + r"(explorador|explorer|archivos)", "open_app", {"app": "explorer"}),
    _mk(r"(abrir|abre) " + _ART + r"(calculadora|calculator)", "open_app", {"app": "calc"}),
    _mk(r"(abrir|abre) " + _ART + r"(terminal|cmd|consola)", "open_app", {"app": "cmd"}),
    _mk(r"(abrir|abre) vscode", "open_app", {"app": "code"}),

    # Ventanas
    _mk(r"(cerrar|cierra) " + _ART + r"(ventana|esto|esta ventana)", "close_window"),
    _mk(r"(minimizar|minimiza) " + _ART + r"(ventana|esto)", "minimize_window"),
    _mk(r"(maximizar|maximiza) " + _ART + r"(ventana|esto)", "maximize_window"),
    _mk(r"(siguiente|cambiar|cambiar ventana|alt tab)", "alt_tab"),

    # Edición
    _mk(r"(copiar|copia|ctrl c)", "hotkey", {"keys": "ctrl+c"}),
    _mk(r"(pegar|pega|ctrl v)", "hotkey", {"keys": "ctrl+v"}),
    _mk(r"(cortar|corta|ctrl x)", "hotkey", {"keys": "ctrl+x"}),
    _mk(r"(deshacer|deshaz|ctrl z)", "hotkey", {"keys": "ctrl+z"}),
    _mk(r"(rehacer|rehaz|ctrl y)", "hotkey", {"keys": "ctrl+y"}),
    _mk(r"(seleccionar todo|selecciona todo|ctrl a)", "hotkey", {"keys": "ctrl+a"}),
    _mk(r"(buscar|busca|ctrl f)", "hotkey", {"keys": "ctrl+f"}),
    _mk(r"(guardar|guarda|ctrl s)", "hotkey", {"keys": "ctrl+s"}),
    _mk(r"(nueva pesta|nueva tab|ctrl t)", "hotkey", {"keys": "ctrl+t"}),
    _mk(r"(cerrar pesta|ctrl w)", "hotkey", {"keys": "ctrl+w"}),

    # Volumen
    _mk(r"(subir|sube|aumentar) " + _ART + r"volumen", "volume_up"),
    _mk(r"(bajar|baja|reducir) " + _ART + r"volumen", "volume_down"),
    _mk(r"(silenciar|mute|sin sonido)", "volume_mute"),

    # Pantalla
    _mk(r"(captura|captura de pantalla|screenshot|foto pantalla)", "screenshot"),
    _mk(r"(zoom in|acercar|ampliar)", "zoom_in"),
    _mk(r"(zoom out|alejar|reducir vista)", "zoom_out"),

    # Scroll
    _mk(r"(scroll arriba|subir p[aá]gina)", "scroll_up"),
    _mk(r"(scroll abajo|bajar p[aá]gina)", "scroll_down"),

    # Escribir texto (MUST be before press_key patterns to avoid "esc" matching "escribe")
    _mk(r"(escribe|escribir|tipea|type)\s+(.+)", "write_text"),

    # Teclas
    _mk(r"(enter|intro|aceptar)", "press_key", {"key": "enter"}),
    _mk(r"(escape|cancelar|esc)", "press_key", {"key": "escape"}),
    _mk(r"(borrar letra|backspace)", "press_key", {"key": "backspace"}),
    _mk(r"(tabulador| tab)", "press_key", {"key": "tab"}),

    # Navegación web
    _mk(r"(recargar|actualizar|ctrl r|f5)", "hotkey", {"keys": "f5"}),
    _mk(r"nueva ventana", "hotkey", {"keys": "ctrl+n"}),
    _mk(r"(imprimir|ctrl p)", "hotkey", {"keys": "ctrl+p"}),
    _mk(r"(historial|ctrl h)", "hotkey", {"keys": "ctrl+h"}),
    _mk(r"(incognito|privado)", "hotkey", {"keys": "ctrl+shift+n"}),

    # Flechas / navegación
    _mk(r"(flecha arriba|ir arriba)", "press_key", {"key": "up"}),
    _mk(r"(flecha abajo|ir abajo)", "press_key", {"key": "down"}),
    _mk(r"(flecha izquierda|ir izquierda|hacia atras)", "press_key", {"key": "left"}),
    _mk(r"(flecha derecha|ir derecha|hacia adelante)", "press_key", {"key": "right"}),
    _mk(r"(página arriba|page up)", "press_key", {"key": "pageup"}),
    _mk(r"(página abajo|page down)", "press_key", {"key": "pagedown"}),

    # Zoom navegador
    _mk(r"(zoom normal|tamaño normal|ctrl 0)", "hotkey", {"keys": "ctrl+0"}),

    # Sistema
    _mk(r"(apagar|shutdown)", "hotkey", {"keys": "alt+F4"}),
    _mk(r"abrir configuración", "hotkey", {"keys": "win+i"}),
    _mk(r"(abrir búsqueda|buscar en windows)", "hotkey", {"keys": "win+s"}),

    # Agente IA — debe ir AL FINAL
    _mk(r"(agente|ia|asistente|gestureos)[,:]?\s*(.+)", "ai_agent"),
    _mk(r"(qu[eé] hay|analiza|describe).{0,10}(pantalla)", "analyze_screen"),
]


class VoiceAssistant:
    def __init__(
        self,
        language: str = VOICE_LANGUAGE,
        rate: int = VOICE_RATE,
        volume: float = VOICE_VOLUME
    ):
        self.language = language
        self.state    = VoiceState.IDLE

        # ── Recognizer ──
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold    = 300
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold     = 0.6

        try:
            self._microphone = sr.Microphone()
        except Exception:
            self._microphone = None

        # ── TTS ──
        try:
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate",   rate)
            self._tts.setProperty("volume", volume)
            self._tts_available = True
        except Exception:
            self._tts_available = False

        self._is_active    = False
        self._is_listening = False

        self._command_queue: queue.Queue = queue.Queue()
        self._result_queue:  queue.Queue = queue.Queue()

        self._listening_thread: Optional[threading.Thread]  = None
        self._processing_thread: Optional[threading.Thread] = None

        self._on_command_callback:      Optional[Callable] = None
        self._on_state_change_callback: Optional[Callable] = None

        self._last_command_time = 0.0
        self._command_cooldown = 2.0
        self._is_speaking = False
        self._voice_enabled = True

    # ─────────────────── Lifecycle ─────────────────────────────────────────

    def start(self):
        if self._is_active or not self._microphone:
            return
        self._is_active = True
        self._calibrate()

        self._listening_thread = threading.Thread(
            target=self._listening_loop, daemon=True)
        self._listening_thread.start()

        self._processing_thread = threading.Thread(
            target=self._processing_loop, daemon=True)
        self._processing_thread.start()

    def stop(self):
        self._is_active    = False
        self._is_listening = False

    def set_state(self, listening: bool):
        self._is_listening = listening
        self._set_state(VoiceState.LISTENING if listening else VoiceState.IDLE)

    def is_listening(self) -> bool:
        return self._is_listening and not self._is_speaking

    def is_voice_enabled(self) -> bool:
        return self._voice_enabled

    def set_voice_enabled(self, enabled: bool):
        self._voice_enabled = enabled
        if not enabled:
            self._is_listening = False

    def get_state(self) -> VoiceState:
        return self.state

    # ─────────────────── Callbacks ─────────────────────────────────────────

    def on_command(self, callback: Callable[[VoiceCommand], None]):
        self._on_command_callback = callback

    def on_state_change(self, callback: Callable[[VoiceState], None]):
        self._on_state_change_callback = callback

    # ─────────────────── TTS ───────────────────────────────────────────────

    def speak(self, text: str, wait: bool = False):
        if not self._tts_available or not self._voice_enabled:
            return
        def _do():
            try:
                self._is_speaking = True
                self._is_listening = False
                self._set_state(VoiceState.SPEAKING)
                time.sleep(0.3)
                self._tts.say(text)
                self._tts.runAndWait()
                time.sleep(0.5)
            except Exception:
                pass
            finally:
                self._is_speaking = False
                self._set_state(VoiceState.IDLE)
        if wait:
            _do()
        else:
            threading.Thread(target=_do, daemon=True).start()

    # ─────────────────── Queued results ────────────────────────────────────

    def process_queued_commands(self) -> List[VoiceCommand]:
        results = []
        while not self._result_queue.empty():
            try:
                cmd = self._result_queue.get_nowait()
                results.append(cmd)
                if self._on_command_callback:
                    self._on_command_callback(cmd)
            except queue.Empty:
                break
        return results

    # ─────────────────── Internals ─────────────────────────────────────────

    def _calibrate(self):
        try:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.8)
        except Exception:
            pass

    def _listening_loop(self):
        while self._is_active:
            if not self._is_listening or self._is_speaking or not self._voice_enabled:
                time.sleep(0.1)
                continue
            try:
                with self._microphone as source:
                    self._set_state(VoiceState.LISTENING)
                    audio = self._recognizer.listen(
                        source, timeout=4, phrase_time_limit=6)
                self._command_queue.put(audio)
            except sr.WaitTimeoutError:
                pass
            except Exception:
                time.sleep(0.2)

    def _processing_loop(self):
        while self._is_active:
            try:
                audio = self._command_queue.get(timeout=1)
            except queue.Empty:
                continue

            self._set_state(VoiceState.PROCESSING)
            text = self._transcribe(audio)

            if text:
                now = time.time()
                if now - self._last_command_time >= self._command_cooldown:
                    self._last_command_time = now
                    cmd = self._match_command(text)
                    # ★ Call callback DIRECTLY — don’t rely on process_queued_commands()
                    if self._on_command_callback:
                        try:
                            self._on_command_callback(cmd)
                        except Exception as e:
                            print(f"[Voice] callback error: {e}")
                    # Also put on queue for any polling consumers
                    self._result_queue.put(cmd)

            self._set_state(VoiceState.IDLE)

    def _transcribe(self, audio) -> Optional[str]:
        """Try whisper first, fall back to Google."""
        for method in ("whisper", "google"):
            try:
                if method == "whisper":
                    return self._recognizer.recognize_whisper(
                        audio, language=self.language).strip()
                else:
                    lang_code = "es-ES"
                    return self._recognizer.recognize_google(
                        audio, language=lang_code).strip()
            except sr.UnknownValueError:
                return None
            except Exception:
                continue
        return None

    def _match_command(self, text: str) -> VoiceCommand:
        text_lower = text.lower().strip()
        for pattern, action, params in COMMAND_PATTERNS:
            m = pattern.search(text_lower)
            if m:
                p = dict(params)
                groups = m.groups()
                # AI agent: grab trailing query from last group
                if action == "ai_agent" and len(groups) >= 2:
                    p["query"] = groups[-1].strip() if groups[-1] else text_lower
                # 'escribe X': grab the text to type from last group
                elif action == "write_text" and len(groups) >= 2:
                    p["text"] = groups[-1].strip() if groups[-1] else ""
                return VoiceCommand(
                    command=text, action=action,
                    params=p, confidence=0.9,
                    timestamp=time.time()
                )
        # Unmatched → send to AI by default
        return VoiceCommand(
            command=text, action="ai_agent",
            params={"query": text}, confidence=0.5,
            timestamp=time.time()
        )

    def _set_state(self, state: VoiceState):
        self.state = state
        if self._on_state_change_callback:
            try:
                self._on_state_change_callback(state)
            except Exception:
                pass

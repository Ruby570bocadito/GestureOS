"""
ActionExecutor — GestureOS
===========================
Ejecuta acciones del sistema a partir de comandos de voz o del agente IA.
Centraliza todo el control del SO para que tanto la voz como la IA lo usen.
"""
import subprocess
import time
import threading
from typing import Optional, Callable, Dict, Any

import pyautogui

# Optional: PIL screenshot
try:
    from PIL import ImageGrab
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


class ActionExecutor:
    """Execute system actions safely from any thread."""

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None,
                 speak_callback: Optional[Callable[[str], None]] = None):
        self._log   = log_callback   or (lambda m: print(f"[Action] {m}"))
        self._speak = speak_callback or (lambda m: None)

        pyautogui.FAILSAFE = False
        pyautogui.PAUSE    = 0.05

    # ─────────────────── Main dispatcher ───────────────────────────────────

    def execute(self, action: str, params: Dict[str, Any] = None) -> bool:
        params = params or {}
        method = getattr(self, f"_do_{action}", None)
        if method:
            try:
                method(params)
                return True
            except Exception as e:
                self._log(f"Error en '{action}': {e}")
                return False
        else:
            self._log(f"Acción desconocida: {action}")
            return False

    # ─────────────── Mouse ─────────────────────────────────────────────────

    def _do_click_left(self, p):
        pyautogui.click()
        self._log("Click izquierdo")

    def _do_click_right(self, p):
        pyautogui.rightClick()
        self._log("Click derecho")

    def _do_double_click(self, p):
        pyautogui.doubleClick()
        self._log("Doble click")

    # ─────────── Write text ──────────────────────────────────────────

    def _do_write(self, p):
        """Type given text with pyautogui (from AI action)."""
        text = p.get("text", "")
        if text:
            pyautogui.write(text, interval=0.03)
            self._log(f"Escribiendo: {text}")

    def _do_write_text(self, p):
        """Voice command 'escribe [texto]' — extract group-2 text."""
        # The regex puts the literal text in p["text"] or as group 2
        text = p.get("text", p.get("query", ""))
        if text:
            pyautogui.write(text, interval=0.03)
            self._log(f"Escribiendo: {text}")

    def _do_toggle_agent_mode(self, p):
        # Handled in main.py; this stub prevents 'unknown action' log
        pass

    # ─────────────── Hotkeys ───────────────────────────────────────────────

    def _do_hotkey(self, p):
        keys = p.get("keys", "")
        if not keys:
            return
        parts = [k.strip() for k in keys.split("+")]
        pyautogui.hotkey(*parts)
        self._log(f"Atajo: {keys}")
        self._speak(f"{keys}")

    def _do_press_key(self, p):
        key = p.get("key", "")
        if key:
            pyautogui.press(key)
            self._log(f"Tecla: {key}")

    # ─────────────── Open apps ─────────────────────────────────────────────

    _APP_COMMANDS: Dict[str, str] = {
        "browser":  "start https://www.google.com",
        "chrome":   "start chrome",
        "firefox":  "start firefox",
        "notepad":  "notepad",
        "explorer": "explorer",
        "calc":     "calc",
        "cmd":      "start cmd",
        "code":     "code",
    }

    def _do_open_app(self, p):
        app = p.get("app", "")
        cmd = self._APP_COMMANDS.get(app)
        if cmd:
            subprocess.Popen(cmd, shell=True)
            self._log(f"Abriendo: {app}")
            self._speak(f"Abriendo {app}")
        else:
            self._log(f"App desconocida: {app}")

    # ─────────────── Window management ─────────────────────────────────────

    def _do_close_window(self, p):
        pyautogui.hotkey("alt", "F4")
        self._log("Cerrando ventana")

    def _do_minimize_window(self, p):
        pyautogui.hotkey("win", "down")
        self._log("Minimizando ventana")

    def _do_maximize_window(self, p):
        pyautogui.hotkey("win", "up")
        self._log("Maximizando ventana")

    def _do_alt_tab(self, p):
        pyautogui.hotkey("alt", "tab")
        self._log("Cambiando ventana")

    def _do_show_desktop(self, p):
        pyautogui.hotkey("win", "d")
        self._log("Mostrando escritorio")

    def _do_lock_screen(self, p):
        pyautogui.hotkey("win", "l")
        self._log("Bloqueando pantalla")

    # ─────────────── Volume ────────────────────────────────────────────────

    def _do_volume_up(self, p):
        for _ in range(5):
            pyautogui.press("volumeup")
        self._log("Volumen +")

    def _do_volume_down(self, p):
        for _ in range(5):
            pyautogui.press("volumedown")
        self._log("Volumen -")

    def _do_volume_mute(self, p):
        pyautogui.press("volumemute")
        self._log("Silencio")

    # ─────────────── Scroll ────────────────────────────────────────────────

    def _do_scroll_up(self, p):
        pyautogui.scroll(5)
        self._log("Scroll arriba")

    def _do_scroll_down(self, p):
        pyautogui.scroll(-5)
        self._log("Scroll abajo")

    # ─────────────── Zoom ──────────────────────────────────────────────────

    def _do_zoom_in(self, p):
        pyautogui.hotkey("ctrl", "+")
        self._log("Zoom in")

    def _do_zoom_out(self, p):
        pyautogui.hotkey("ctrl", "-")
        self._log("Zoom out")

    # ─────────────── Screenshot ────────────────────────────────────────────

    def _do_screenshot(self, p) -> Optional[str]:
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            path = f"screenshot_{ts}.png"
            pyautogui.screenshot(path)
            self._log(f"Captura guardada: {path}")
            self._speak("Captura tomada")
            return path
        except Exception as e:
            self._log(f"Error captura: {e}")
            return None

    # ─────────────── Analyze screen (for AI) ───────────────────────────────

    def take_screenshot_b64(self) -> Optional[str]:
        """Returns base64 PNG of current screen for AI vision."""
        if not _PIL_OK:
            return None
        try:
            import io, base64
            img = ImageGrab.grab()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            return None

    def _do_analyze_screen(self, p):
        # Fires analyze request — main.py will send to AI
        self._log("Analizando pantalla...")
        # Actual handling in main.py via callback

    # ─────────────── Keyboard toggle (delegated) ───────────────────────────

    def _do_toggle_keyboard(self, p):
        # main.py listens for this via the voice command callback
        self._log("Toggle teclado virtual")

    def _do_stop_voice(self, p):
        self._log("Deteniendo voz")

    # ─────────────── AI agent responder ────────────────────────────────────

    def _do_respond(self, p):
        text = p.get("text", "")
        if text:
            self._log(f"IA: {text}")
            self._speak(text)

    def _do_ai_agent(self, p):
        # Query handled externally by main.py
        self._log(f"Consulta IA: {p.get('query', '')}")

    def _do_error(self, p):
        self._log(f"Error: {p.get('message', '')}")

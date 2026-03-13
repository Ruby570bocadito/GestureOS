import sys
import threading
import time
import cv2
import numpy as np
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, pyqtSlot, QMetaObject, Qt

from src.ui.main_window import MainWindow
from src.ui.overlay import OverlayWidget
from src.core.gesture_tracker import GestureTracker
from src.core.gesture_recognizer import GestureRecognizer, GestureType
from src.input.virtual_mouse import VirtualMouse
from src.input.virtual_keyboard import VirtualKeyboard
from src.ui.virtual_keyboard_widget import VirtualKeyboardWidget
from src.ai.desktop_agent import DesktopAgent
from src.ai.vision_helper import VisionHelper
from src.utils.system_control import SystemController
from src.utils.action_executor import ActionExecutor
from src.core.config import OVERLAY_FPS

# Voice lazy loaded to avoid startup delay
VoiceAssistant = None


class GestureOS:
    def __init__(self):
        self.app = QApplication(sys.argv)

        self.main_window = MainWindow()
        self.main_window.start_system.connect(self.start)
        self.main_window.stop_system.connect(self.stop)
        self.main_window.mouse_enabled.stateChanged.connect(self._on_mouse_toggled)
        self.main_window.keyboard_enabled.stateChanged.connect(self._on_keyboard_toggled)
        self.main_window.voice_enabled.stateChanged.connect(self._on_voice_toggled)
        self.main_window.ai_enabled.stateChanged.connect(self._on_ai_toggled)

        self.overlay = OverlayWidget()
        self.overlay.mouse_mode_changed.connect(self._on_mouse_mode_changed)
        self.overlay.keyboard_mode_changed.connect(self._on_keyboard_mode_changed)

        self.gesture_tracker = GestureTracker()
        self.gesture_recognizer = GestureRecognizer()

        self.virtual_mouse = VirtualMouse()
        self.virtual_keyboard = VirtualKeyboard()

        # Real Qt keyboard window (must be created on the main thread)
        self.keyboard_widget = VirtualKeyboardWidget()
        self.keyboard_widget.closed.connect(self._on_keyboard_widget_closed)

        self._voice_assistant_instance = None
        self._voice_initialized = False

        try:
            self.desktop_agent = DesktopAgent()
            self.desktop_agent.on_action(self._on_agent_action)
            self.desktop_agent.on_state_change(self._on_agent_state_changed)
        except Exception as e:
            print(f"Desktop agent init error: {e}")
            self.desktop_agent = None

        self.vision_helper = VisionHelper()
        self.system_controller = SystemController()

        # Central action executor (voice + AI both use this)
        self.action_executor = ActionExecutor(
            log_callback=self.main_window.log_message,
            speak_callback=lambda t: self.voice_assistant.speak(t) if self.voice_assistant else None
        )

        self._is_running = False
        self._capture_thread = None
        self._processing_timer = None
        self._keyboard_toggle_cooldown = 0
        self._agent_mode = False   # When True, all voice goes directly to AI agent

        # Zoom tracking
        self._zoom_prev_distance: float | None = None

        # Keyboard shortcut tracking (left hand double-gesture)
        self._shortcut_last_gesture = ""
        self._shortcut_last_time   = 0.0
        self._shortcut_cooldown    = 1.5   # seconds between shortcut triggers

        self._setup_callbacks()

    @property
    def voice_assistant(self):
        if self._voice_initialized:
            return self._voice_assistant_instance
        self._voice_initialized = True
        try:
            from src.input.voice_assistant import VoiceAssistant
            self._voice_assistant_instance = VoiceAssistant()
            self._voice_assistant_instance.on_command(self._on_voice_command)
            self._voice_assistant_instance.on_state_change(self._on_voice_state_changed)
            self.main_window.log_message("Asistente de voz cargado")
        except Exception as e:
            self._voice_assistant_instance = None
            self.main_window.log_message(f"Voz no disponible: {e}")
        return self._voice_assistant_instance

    def _setup_callbacks(self):
        self.virtual_mouse.set_gesture_callback(self._on_mouse_gesture)
        self.virtual_keyboard.set_gesture_callback(self._on_keyboard_gesture)
        self.main_window.speed_changed.connect(self._on_speed_changed)

    def _on_speed_changed(self, level: int):
        """Translate slider 1-5 into smoothing + speed values."""
        # level 1=slowest, 3=default, 5=fastest
        smoothing_map = {1: 0.12, 2: 0.20, 3: 0.30, 4: 0.40, 5: 0.55}
        speed_map     = {1: 0.9,  2: 1.5,  3: 2.2,  4: 3.2,  5: 4.5}
        self.virtual_mouse._smoothing  = smoothing_map.get(level, 0.30)
        self.virtual_mouse._speed_mult = speed_map.get(level, 2.2)
        self.main_window.log_message(f"Velocidad ratón: {'⬛' * level}{'□' * (5 - level)} ({level}/5)")

    def start(self):
        if self._is_running:
            return

        self._is_running = True
        self._keyboard_toggle_cooldown = 0

        self.main_window.log_message("Iniciando GestureOS...")

        try:
            self.gesture_tracker.release()
        except:
            pass

        self.gesture_tracker = GestureTracker()

        if self.voice_assistant:
            try:
                self.voice_assistant.start()
                self.main_window.log_message("Asistente de voz iniciado")
            except Exception as e:
                self.main_window.log_message(f"Error al iniciar voz: {e}")

        if self.desktop_agent:
            try:
                self.desktop_agent.start()
                self.main_window.log_message("Agente IA iniciado")
            except Exception as e:
                self.main_window.log_message(f"Error al iniciar IA: {e}")

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

        self.overlay.show()
        self.main_window.show()

        self.main_window.log_message("Sistema iniciado correctamente - ¡Usa la palma para mover el mouse!")

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False

        time.sleep(0.5)

        if self.voice_assistant:
            try:
                self.voice_assistant.stop()
            except:
                pass

        if self.desktop_agent:
            try:
                self.desktop_agent.stop()
            except:
                pass

        self.overlay.hide()

        self.main_window.log_message("Sistema detenido")

    def _capture_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.main_window.log_message("Error: No se pudo abrir la cámara")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        try:
            while self._is_running:
                try:
                    ret, frame = cap.read()
                    if not ret:
                        time.sleep(0.01)
                        continue

                    frame = cv2.flip(frame, 1)

                    hands = self.gesture_tracker.process_frame(frame)

                    unique_hands = []
                    seen_positions = []
                    for hand in hands:
                        pos = hand.palm_center
                        is_duplicate = False
                        for seen_pos in seen_positions:
                            if abs(pos[0] - seen_pos[0]) < 50 and abs(pos[1] - seen_pos[1]) < 50:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            unique_hands.append(hand)
                            seen_positions.append(pos)

                    hands = unique_hands

                    left_hand = None
                    right_hand = None

                    for hand in hands:
                        gesture_state = self.gesture_recognizer.recognize(hand)
                        gesture_name = gesture_state.gesture.value
                        handedness = hand.handedness

                        if handedness == "Left":
                            left_hand = (hand, gesture_state)
                            display_hand = "🖐 Mover"   # left = cursor
                        else:
                            right_hand = (hand, gesture_state)
                            display_hand = "👆 Acción"  # right = clicks

                        self.overlay.update_gesture(f"{display_hand}: {gesture_name}")
                        self.main_window.update_gesture(f"{display_hand}: {gesture_name}")

                    if self.virtual_keyboard.is_visible and (left_hand or right_hand):
                        hand_to_use = left_hand[0] if left_hand else right_hand[0]
                        gesture_to_use = (left_hand[1] if left_hand else right_hand[1]).gesture
                        self.virtual_keyboard.handle_gesture(
                            gesture_to_use,
                            hand_to_use.palm_center
                        )

                    # LEFT hand → move / drag cursor
                    if self.virtual_mouse.is_enabled and left_hand:
                        hand, gesture_state = left_hand
                        self.virtual_mouse.update_move(
                            hand.palm_center,
                            gesture_state.gesture,
                        )

                    # ── RIGHT hand → clicks / scroll
                    if self.virtual_mouse.is_enabled and right_hand:
                        hand, gesture_state = right_hand
                        old_click_count = self.virtual_mouse._fist_click_count
                        self.virtual_mouse.update_action(
                            gesture_state.gesture,
                            hand.palm_center,
                        )
                        if self.virtual_mouse._fist_click_count != old_click_count:
                            self.overlay.add_log("Click")

                    # ── ZOOM: both hands open palm — spread/pinch = Ctrl+scroll ──
                    if (self.virtual_mouse.is_enabled and
                            left_hand and right_hand and len(hands) == 2):
                        lgs = left_hand[1].gesture.value
                        rgs = right_hand[1].gesture.value
                        if lgs == "open_palm" and rgs == "open_palm":
                            self._zoom_prev_distance = self.virtual_mouse.handle_zoom(
                                left_hand[0].palm_center,
                                right_hand[0].palm_center,
                                self._zoom_prev_distance
                            )
                            self.overlay.set_active_mode("zoom")
                        else:
                            self._zoom_prev_distance = None

                    # ── KEYBOARD SHORTCUTS: right hand combos ──
                    if right_hand:
                        rgs = right_hand[1].gesture.value
                        now = time.time()
                        if now - self._shortcut_last_time > self._shortcut_cooldown:
                            # Ctrl+C: two quick fists
                            if (rgs == "fist" and
                                    self._shortcut_last_gesture == "fist" and
                                    now - self._shortcut_last_time < 0.8):
                                import pyautogui as _pag
                                _pag.hotkey("ctrl", "c")
                                self.overlay.add_log("Ctrl+C")
                                self.main_window.log_message("Atajo: Ctrl+C")
                                self._shortcut_last_time = now
                            # Ctrl+Z: two quick thumbs-down
                            elif (rgs == "thumbs_down" and
                                    self._shortcut_last_gesture == "thumbs_down" and
                                    now - self._shortcut_last_time < 0.8):
                                import pyautogui as _pag
                                _pag.hotkey("ctrl", "z")
                                self.overlay.add_log("Ctrl+Z")
                                self.main_window.log_message("Atajo: Ctrl+Z")
                                self._shortcut_last_time = now
                            # Ctrl+V: thumbs-up then thumbs-down quick
                            elif (rgs == "thumbs_up" and
                                    self._shortcut_last_gesture == "thumbs_down" and
                                    now - self._shortcut_last_time < 0.8):
                                import pyautogui as _pag
                                _pag.hotkey("ctrl", "v")
                                self.overlay.add_log("Ctrl+V")
                                self.main_window.log_message("Atajo: Ctrl+V")
                                self._shortcut_last_time = now
                        self._shortcut_last_gesture = rgs

                    # ── Overlay: update dwell progress + active mode ──
                    dwell_prog = self.virtual_mouse.dwell_progress
                    self.overlay.set_dwell_progress(dwell_prog)
                    if dwell_prog > 0.02:
                        self.overlay.set_active_mode("dwell")
                    elif self.virtual_mouse.state.value == "dragging":
                        self.overlay.set_active_mode("drag")
                    elif self.virtual_mouse.state.value == "scrolling":
                        self.overlay.set_active_mode("scroll")
                    elif self.virtual_mouse._dragging:
                        self.overlay.set_active_mode("select")
                    else:
                        if not (left_hand and right_hand and
                                left_hand[1].gesture.value == "open_palm" and
                                right_hand[1].gesture.value == "open_palm"):
                            self.overlay.set_active_mode("")


                    if len(hands) == 2 and left_hand and right_hand:
                        left_gesture = left_hand[1].gesture.value
                        right_gesture = right_hand[1].gesture.value

                        if (left_gesture == "thumbs_up" and right_gesture == "thumbs_up" and
                                (time.time() - self._keyboard_toggle_cooldown) > 3.0):
                            try:
                                # Use QMetaObject.invokeMethod to cross from
                                # background thread to Qt main thread safely.
                                if not self.virtual_keyboard.is_visible:
                                    self.virtual_keyboard.show()
                                    self.overlay._keyboard_enabled = True
                                    QMetaObject.invokeMethod(
                                        self.keyboard_widget,
                                        "show_keyboard",
                                        Qt.ConnectionType.QueuedConnection
                                    )
                                    QMetaObject.invokeMethod(
                                        self.main_window,
                                        "_invoke_keyboard_on",
                                        Qt.ConnectionType.QueuedConnection
                                    )
                                else:
                                    self.virtual_keyboard.hide()
                                    self.overlay._keyboard_enabled = False
                                    QMetaObject.invokeMethod(
                                        self.keyboard_widget,
                                        "hide_keyboard",
                                        Qt.ConnectionType.QueuedConnection
                                    )
                                    QMetaObject.invokeMethod(
                                        self.main_window,
                                        "_invoke_keyboard_off",
                                        Qt.ConnectionType.QueuedConnection
                                    )
                            except Exception as e:
                                print(f"Error keyboard toggle: {e}")
                            self._keyboard_toggle_cooldown = time.time()

                    self.overlay.update_frame(frame)
                    self.overlay.update_hands(hands)
                    self.overlay._fps = self.gesture_tracker.fps

                    time.sleep(1 / OVERLAY_FPS)
                except Exception as e:
                    print(f"Error in capture loop: {e}")
                    time.sleep(0.1)
        finally:
            cap.release()

        cap.release()

    def _on_mouse_toggled(self, state):
        enabled = bool(state)
        self.virtual_mouse.enable() if enabled else self.virtual_mouse.disable()
        self.overlay.set_mouse_enabled(enabled)
        self.main_window.log_message(f"Mouse {'activado' if enabled else 'desactivado'}")

    def _on_keyboard_toggled(self, state):
        enabled = bool(state)
        if enabled:
            self.virtual_keyboard.show()
            self.keyboard_widget.show_keyboard()
        else:
            self.virtual_keyboard.hide()
            self.keyboard_widget.hide_keyboard()
        self.overlay.set_keyboard_enabled(enabled)
        self.main_window.log_message(f"Teclado {'activado' if enabled else 'desactivado'}")

    def _on_keyboard_widget_closed(self):
        """Called when user clicks the ✕ button on the keyboard widget."""
        self.virtual_keyboard.hide()
        self.overlay.set_keyboard_enabled(False)
        self.main_window.set_keyboard_enabled(False)
        self.main_window.log_message("Teclado cerrado")

    @pyqtSlot()
    def _show_keyboard_widget(self):
        """Slot called on the main Qt thread to show the keyboard."""
        self.virtual_keyboard.show()
        self.keyboard_widget.show_keyboard()
        self.overlay.set_keyboard_enabled(True)
        self.main_window.set_keyboard_enabled(True)
        self.main_window.log_message("Teclado activado (👍👍)")

    @pyqtSlot()
    def _hide_keyboard_widget(self):
        """Slot called on the main Qt thread to hide the keyboard."""
        self.virtual_keyboard.hide()
        self.keyboard_widget.hide_keyboard()
        self.overlay.set_keyboard_enabled(False)
        self.main_window.set_keyboard_enabled(False)
        self.main_window.log_message("Teclado cerrado (👍👍)")

    def _on_voice_toggled(self, state):
        enabled = bool(state)
        if self.voice_assistant:
            if enabled:
                try:
                    self.voice_assistant.start()
                    self.voice_assistant.set_state(True)
                except:
                    pass
            else:
                try:
                    self.voice_assistant.set_state(False)
                except:
                    pass
        self.main_window.log_message(f"Voz {'activada' if enabled else 'desactivada'}")

    def _on_ai_toggled(self, state):
        enabled = bool(state)
        if self.desktop_agent:
            if enabled:
                try:
                    self.desktop_agent.start()
                except:
                    pass
            else:
                try:
                    self.desktop_agent.stop()
                except:
                    pass
        self.main_window.log_message(f"IA {'activada' if enabled else 'desactivada'}")

    def _on_mouse_mode_changed(self, enabled):
        self.main_window.set_mouse_enabled(enabled)

    def _on_keyboard_mode_changed(self, enabled):
        self.main_window.set_keyboard_enabled(enabled)

    def _on_mouse_gesture(self, gesture: str):
        self.main_window.log_message(f"Gesto mouse: {gesture}")

    def _on_keyboard_gesture(self, key: str):
        self.main_window.log_message(f"Tecla presionada: {key}")

    def _on_voice_command(self, cmd):
        """Dispatches a VoiceCommand (or raw str for compat) through ActionExecutor."""
        if isinstance(cmd, str):
            action, params, text = "ai_agent", {"query": cmd}, cmd
        else:
            action, params, text = cmd.action, cmd.params, cmd.command

        self.main_window.log_message(f"🎤 '{text}' → {action}")
        self.overlay.add_log(f"🎤 {text[:22]}")

        # --- Agent direct mode: everything goes to AI ---
        if self._agent_mode and action not in ("stop_agent_mode",):
            if self.desktop_agent and self.main_window.ai_enabled.isChecked():
                threading.Thread(
                    target=self._send_to_agent,
                    args=(text, None),
                    daemon=True
                ).start()
            return

        # Toggle agent mode on/off
        if action == "toggle_agent_mode":
            self._agent_mode = not self._agent_mode
            state = "ACTIVO" if self._agent_mode else "desactivado"
            self.main_window.log_message(f"🤖 Modo agente: {state}")
            self.overlay.add_log(f"🤖 Modo agente {state}")
            if self.voice_assistant:
                self.voice_assistant.speak(f"Modo agente {state}")
            return

        # Toggle keyboard on main thread using QTimer (safe from any thread)
        if action == "toggle_keyboard":
            is_on = self.virtual_keyboard.is_visible
            if is_on:
                QTimer.singleShot(0, self._hide_keyboard_widget)
            else:
                QTimer.singleShot(0, self._show_keyboard_widget)
            return

        # AI agent query
        if action in ("ai_agent", "analyze_screen"):
            if self.desktop_agent and self.main_window.ai_enabled.isChecked():
                images = None
                if action == "analyze_screen":
                    images = [self.action_executor.take_screenshot_b64()]
                    images = [i for i in images if i]
                query = params.get("query", text)
                threading.Thread(
                    target=self._send_to_agent,
                    args=(query, images or None),
                    daemon=True
                ).start()
            return

        if action == "stop_voice":
            if self.voice_assistant:
                self.voice_assistant.set_state(False)
            return

        # All other actions go to executor
        self.action_executor.execute(action, params)

    def _on_voice_state_changed(self, state):
        self.main_window.update_status(f"Voz: {state.value}")

    def _send_to_agent(self, query: str, images=None):
        """Run AI agent query in background thread and execute the result."""
        try:
            response = self.desktop_agent.ask(query, images=images)
            action   = response.get("action", "respond")
            params   = response.get("params", {})
            expl     = response.get("explanation", "")
            text     = params.get("text", "")
            
            self.main_window.log_message(f"🤖 IA: {expl}")
            self.overlay.add_log(f"🤖 {expl[:22]}")
            
            self.action_executor.execute(action, params)
            
            if text and self.voice_assistant and self.voice_assistant.is_voice_enabled():
                short_text = text[:150] + "..." if len(text) > 150 else text
                time.sleep(0.5)
                self.voice_assistant.speak(short_text)
                
        except Exception as e:
            self.main_window.log_message(f"Error agente: {e}")

    def _on_agent_action(self, action):
        """Callback from DesktopAgent when it decides an action."""
        self.action_executor.execute(action.action_type, action.params)

    def _on_agent_state_changed(self, state):
        self.main_window.update_status(f"IA: {state.value}")

    def run(self):
        self.main_window.show()
        return self.app.exec()


def main():
    gestureos = GestureOS()
    return gestureos.run()


if __name__ == "__main__":
    sys.exit(main())

"""
VirtualMouse — HandsControl
========================
Roles por mano:

  MANO IZQUIERDA  → mueve el cursor
      🖐️ Palma / 👍 Thumb Up   = mover cursor
      🤏 Pinch                  = arrastrar (drag)
      ✌️ Dos dedos              = scroll natural (trackpad)
      🖐️ Quieta 1.5s            = DWELL CLICK automático

  MANO DERECHA   → acciones
      ✊ Puño / 👍 Thumb Up     = click izquierdo
      👎 Thumb Down             = click derecho
      ✌️ Peace + mover          = seleccionar texto
      ☝️ Un dedo arriba         = scroll clásico
      🤌 Index wink             = click suave (wink click)
"""
import time
import threading
import logging
from typing import Optional, Tuple, Callable
from enum import Enum

import pyautogui
import numpy as np

from src.core.config import (
    MOUSE_SMOOTHING,
    MOUSE_SPEED_MULTIPLIER,
    MOUSE_DEADZONE,
    OVERLAY_CAMERA_WIDTH,
    OVERLAY_CAMERA_HEIGHT,
    CLICK_COOLDOWN,
    SCROLL_COOLDOWN,
    DWELL_THRESHOLD,
    DWELL_DEADZONE,
    ZOOM_DELTA_THRESHOLD,
    ZOOM_SCROLL_DIVISOR,
    SCROLL_UNITS_DIVISOR,
)
from src.core.gesture_recognizer import GestureType

logger = logging.getLogger("handscontrol.virtual_mouse")


class MouseState(Enum):
    IDLE      = "idle"
    MOVING    = "moving"
    DRAGGING  = "dragging"
    SCROLLING = "scrolling"
    DWELL     = "dwell"


class VirtualMouse:
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

        screen_w, screen_h = pyautogui.size()
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._cam_w    = OVERLAY_CAMERA_WIDTH
        self._cam_h    = OVERLAY_CAMERA_HEIGHT

        self._smoothing  = MOUSE_SMOOTHING
        self._speed_mult = MOUSE_SPEED_MULTIPLIER
        self._deadzone   = MOUSE_DEADZONE

        self.state      = MouseState.IDLE
        self.is_enabled = True

        self._last_click_time  = 0.0
        self._click_cooldown   = CLICK_COOLDOWN

        self._last_scroll_time = 0.0
        self._scroll_cooldown  = SCROLL_COOLDOWN
        self._prev_scroll_y: Optional[int] = None

        self._dragging = False

        self._dwell_threshold   = DWELL_THRESHOLD
        self._dwell_deadzone    = DWELL_DEADZONE
        self._dwell_start_time  = 0.0
        self._dwell_last_pos: Optional[Tuple[int, int]] = None
        self._dwell_clicked     = False
        self.dwell_progress     = 0.0

        self._prev_right_gesture = GestureType.UNKNOWN

        self._gesture_callback: Optional[Callable] = None
        self._lock = threading.Lock()

        self._fist_click_count = 0

    def set_gesture_callback(self, callback: Callable):
        self._gesture_callback = callback

    def enable(self):
        self.is_enabled = True

    def disable(self):
        self.is_enabled = False
        self._release_drag()

    def get_state(self) -> MouseState:
        return self.state

    def get_position(self) -> Tuple[int, int]:
        pos = pyautogui.position()
        return (pos.x, pos.y)

    def update_move(self, hand_position: Tuple[int, int], gesture: GestureType):
        """Call every frame with the LEFT hand data."""
        if not self.is_enabled:
            return

        with self._lock:
            gv = gesture.value

            if gv in ("open_palm", "thumbs_up"):
                self._release_drag()
                self.state = MouseState.MOVING
                target = self._to_screen(hand_position)
                self._smooth_move(target)
                self._update_dwell(hand_position)

            elif gv == "pinch":
                self._dwell_reset()
                self.state = MouseState.DRAGGING
                target = self._to_screen(hand_position)
                if not self._dragging:
                    try:
                        pyautogui.mouseDown(_pause=False)
                        self._dragging = True
                        self._cb("drag_start")
                    except Exception as e:
                        logger.error(f"Drag start failed: {e}")
                self._smooth_move(target)

            elif gv == "two_finger_scroll":
                self._dwell_reset()
                self._release_drag()
                self.state = MouseState.SCROLLING
                self._handle_scroll(hand_position, time.time())

            else:
                self._release_drag()
                self._dwell_reset()
                self.state = MouseState.IDLE

    def update_action(self, gesture: GestureType,
                      hand_position: Optional[Tuple[int, int]] = None):
        """Call every frame with the RIGHT hand data."""
        if not self.is_enabled:
            return

        with self._lock:
            current_time = time.time()
            gv = gesture.value
            prev_gv = self._prev_right_gesture.value

            if gv in ("fist", "thumbs_up") and prev_gv not in ("fist", "thumbs_up"):
                self._handle_click("left", current_time)
                self._fist_click_count += 1

            elif gv == "thumbs_down" and prev_gv != "thumbs_down":
                self._handle_click("right", current_time)

            elif gv == "index_click" and prev_gv != "index_click":
                self._handle_click("left", current_time)
                self._fist_click_count += 1
                self._cb("wink_click")

            elif gv == "peace" and hand_position:
                target = self._to_screen(hand_position)
                if not self._dragging:
                    try:
                        pyautogui.mouseDown(_pause=False)
                        self._dragging = True
                        self._cb("select_start")
                    except Exception as e:
                        logger.error(f"Select start failed: {e}")
                self._smooth_move(target)
                self.state = MouseState.DRAGGING

            elif gv == "pointing_up" and hand_position:
                self._release_drag()
                self._handle_scroll(hand_position, current_time)

            else:
                if prev_gv == "peace" and gv != "peace":
                    self._release_drag()
                if gv not in ("pointing_up", "two_finger_scroll"):
                    self._prev_scroll_y = None

            self._prev_right_gesture = gesture

    def handle_zoom(self, left_pos: Tuple[int, int], right_pos: Tuple[int, int],
                    prev_distance: Optional[float]) -> float:
        dx = right_pos[0] - left_pos[0]
        dy = right_pos[1] - left_pos[1]
        dist = (dx * dx + dy * dy) ** 0.5

        if prev_distance is not None:
            delta = dist - prev_distance
            if abs(delta) > ZOOM_DELTA_THRESHOLD:
                scroll_amount = int(delta / ZOOM_SCROLL_DIVISOR)
                if scroll_amount != 0:
                    try:
                        pyautogui.keyDown("ctrl")
                        pyautogui.scroll(scroll_amount, _pause=False)
                        pyautogui.keyUp("ctrl")
                        self._cb(f"zoom_{'in' if scroll_amount > 0 else 'out'}")
                    except Exception as e:
                        logger.error(f"Zoom failed: {e}")
        return dist

    def _to_screen(self, cam_pos: Tuple[int, int]) -> np.ndarray:
        sx = int((cam_pos[0] / self._cam_w) * self._screen_w)
        sy = int((cam_pos[1] / self._cam_h) * self._screen_h)
        sx = max(0, min(self._screen_w - 1, sx))
        sy = max(0, min(self._screen_h - 1, sy))
        return np.array([sx, sy], dtype=float)

    def _smooth_move(self, target: np.ndarray):
        current = np.array(pyautogui.position(), dtype=float)
        delta   = target - current
        if np.linalg.norm(delta) < self._deadzone:
            return
        smoothed = current + delta * self._smoothing
        try:
            pyautogui.moveTo(int(smoothed[0]), int(smoothed[1]), _pause=False)
        except Exception as e:
            logger.error(f"Move failed: {e}")

    def _handle_click(self, button: str, current_time: float):
        if current_time - self._last_click_time < self._click_cooldown:
            return
        self._last_click_time = current_time
        try:
            if button == "left":
                pyautogui.click(_pause=False)
                self._cb("click")
            else:
                pyautogui.rightClick(_pause=False)
                self._cb("right_click")
        except Exception as e:
            logger.error(f"Click failed: {e}")

    def _handle_scroll(self, hand_position: Tuple[int, int], current_time: float):
        if current_time - self._last_scroll_time < self._scroll_cooldown:
            return
        if self._prev_scroll_y is None:
            self._prev_scroll_y = hand_position[1]
            return
        delta_y = hand_position[1] - self._prev_scroll_y
        scroll_units = int(delta_y / SCROLL_UNITS_DIVISOR)
        if scroll_units != 0:
            try:
                pyautogui.scroll(-scroll_units, _pause=False)
                self._cb(f"scroll_{'down' if scroll_units > 0 else 'up'}")
            except Exception as e:
                logger.error(f"Scroll failed: {e}")
            self._last_scroll_time = current_time
        self._prev_scroll_y = hand_position[1]

    def _update_dwell(self, pos: Tuple[int, int]):
        now = time.time()

        if self._dwell_last_pos is None:
            self._dwell_last_pos = pos
            self._dwell_start_time = now
            self._dwell_clicked = False
            self.dwell_progress = 0.0
            return

        dx = abs(pos[0] - self._dwell_last_pos[0])
        dy = abs(pos[1] - self._dwell_last_pos[1])

        if dx > self._dwell_deadzone or dy > self._dwell_deadzone:
            self._dwell_last_pos = pos
            self._dwell_start_time = now
            self._dwell_clicked = False
            self.dwell_progress = 0.0
            return

        elapsed = now - self._dwell_start_time
        self.dwell_progress = min(elapsed / self._dwell_threshold, 1.0)

        if elapsed >= self._dwell_threshold and not self._dwell_clicked:
            self._dwell_clicked = True
            self.dwell_progress = 1.0
            try:
                pyautogui.click(_pause=False)
                self._cb("dwell_click")
            except Exception as e:
                logger.error(f"Dwell click failed: {e}")

    def _dwell_reset(self):
        self._dwell_last_pos = None
        self._dwell_start_time = 0.0
        self._dwell_clicked = False
        self.dwell_progress = 0.0

    def _release_drag(self):
        if self._dragging:
            try:
                pyautogui.mouseUp(_pause=False)
                self._cb("drag_end")
            except Exception as e:
                logger.error(f"Drag release failed: {e}")
            self._dragging = False

    def _cb(self, action: str):
        if self._gesture_callback:
            try:
                self._gesture_callback(action)
            except Exception as e:
                logger.error(f"Gesture callback '{action}' failed: {e}")

    def update(self, hand_position, gesture, finger_states, hand="left"):
        self.update_move(hand_position, gesture)

    def update_click(self, gesture, hand="right"):
        self.update_action(gesture)

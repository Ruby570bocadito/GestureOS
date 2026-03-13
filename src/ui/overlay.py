import cv2
import numpy as np
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPen, QBrush

from src.core.config import OVERLAY_CAMERA_WIDTH, OVERLAY_CAMERA_HEIGHT, OVERLAY_OPACITY

# Emoji/icon mapping per gesture value
GESTURE_ICONS = {
    "open_palm":        ("🖐️", "#00ff88"),
    "fist":             ("✊", "#ff6060"),
    "pointing_up":      ("☝️", "#60c0ff"),
    "peace":            ("✌️", "#c080ff"),
    "thumbs_up":        ("👍", "#ffdd00"),
    "thumbs_down":      ("👎", "#ff8800"),
    "ok_sign":          ("👌", "#00ffdd"),
    "pinch":            ("🤏", "#ff80ff"),
    "two_finger_tap":   ("✌️", "#8080ff"),
    "three_finger_tap": ("🤟", "#88ff00"),
    "index_click":      ("🤌", "#ff44aa"),
    "two_finger_scroll":("✌️", "#44ddff"),
    "swipe_left":       ("👈", "#ffaa00"),
    "swipe_right":      ("👉", "#ffaa00"),
    "swipe_up":         ("👆", "#ffaa00"),
    "swipe_down":       ("👇", "#ffaa00"),
    "unknown":          ("❓", "#888888"),
}


class OverlayWidget(QWidget):
    gesture_detected = pyqtSignal(str)
    mouse_mode_changed = pyqtSignal(bool)
    keyboard_mode_changed = pyqtSignal(bool)

    def __init__(
        self,
        width: int = OVERLAY_CAMERA_WIDTH,
        height: int = OVERLAY_CAMERA_HEIGHT,
        parent=None
    ):
        super().__init__(parent)

        self.frame_width = width
        self.frame_height = height

        self.setFixedSize(width, height)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        screen_width = self.screen().geometry().width()
        screen_height = self.screen().geometry().height()
        self.move(screen_width - width - 20, 20)

        self._current_frame = None
        self._hands_data = []
        self._gesture_info = ""
        self._gesture_raw = ""          # raw gesture value for icon lookup
        self._mouse_enabled = True
        self._keyboard_enabled = False
        self._fps = 0
        self._log_messages = []
        self._max_log_messages = 4
        self._dwell_progress = 0.0      # 0.0-1.0 for dwell ring
        self._active_mode = ""          # e.g. "zoom", "select", "dwell"

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update)
        self._update_timer.start(33)

    # ─────────────── Public setters ────────────────────────────────────────

    def add_log(self, message: str):
        self._log_messages.append(message)
        if len(self._log_messages) > self._max_log_messages:
            self._log_messages.pop(0)

    def update_frame(self, frame: np.ndarray):
        self._current_frame = frame.copy()

    def update_hands(self, hands_data):
        self._hands_data = hands_data

    def update_gesture(self, gesture_name: str):
        self._gesture_info = gesture_name
        # Extract raw gesture name for icon lookup
        if ": " in gesture_name:
            self._gesture_raw = gesture_name.split(": ")[-1].strip()
        self.gesture_detected.emit(gesture_name)

    def set_mouse_enabled(self, enabled: bool):
        self._mouse_enabled = enabled
        self.mouse_mode_changed.emit(enabled)

    def set_keyboard_enabled(self, enabled: bool):
        self._keyboard_enabled = enabled
        self.keyboard_mode_changed.emit(enabled)

    def set_dwell_progress(self, progress: float):
        self._dwell_progress = max(0.0, min(1.0, progress))

    def set_active_mode(self, mode: str):
        self._active_mode = mode

    # ─────────────── Paint ─────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = None
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            # ── Camera frame ──
            painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
            if self._current_frame is not None:
                try:
                    frame_rgb = cv2.cvtColor(self._current_frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qt_image)
                    painter.drawPixmap(0, 0, pixmap.scaled(
                        self.frame_width, self.frame_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                except Exception:
                    pass

            # ── Semi-transparent bottom bar for text ──
            bar_h = 56
            painter.fillRect(0, self.frame_height - bar_h, self.frame_width, bar_h,
                             QColor(0, 0, 0, 160))

            # ── Status indicators (top-left) ──
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            dot_colors = [
                (self._mouse_enabled, "Mouse", QColor(0, 220, 80), QColor(180, 60, 60)),
                (self._keyboard_enabled, "Teclado", QColor(0, 200, 255), QColor(180, 60, 60)),
            ]
            y_off = 18
            for enabled, label, on_col, off_col in dot_colors:
                col = on_col if enabled else off_col
                painter.setBrush(QBrush(col))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(6, y_off - 8, 9, 9)
                painter.setPen(col)
                painter.drawText(20, y_off, f"{label}: {'ON' if enabled else 'OFF'}")
                y_off += 16

            # ── FPS (top-right) ──
            painter.setPen(QColor(100, 200, 255))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(self.frame_width - 55, 14, f"FPS: {self._fps}")

        except Exception:
            pass
        painter.setPen(QColor(100, 200, 255))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(self.frame_width - 55, 14, f"FPS: {self._fps}")

        # ── Big gesture icon (center bottom) ──
        if self._gesture_raw:
            icon_info = GESTURE_ICONS.get(self._gesture_raw, ("❓", "#888888"))
            icon_text, icon_color = icon_info
            col = QColor(icon_color)

            # Pill background
            pill_w, pill_h = 110, 44
            pill_x = (self.frame_width - pill_w) // 2
            pill_y = self.frame_height - bar_h + 6
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(QPen(col, 1.5))
            painter.drawRoundedRect(pill_x, pill_y, pill_w, pill_h, 12, 12)

            # Icon
            painter.setFont(QFont("Segoe UI Emoji", 16))
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(pill_x + 6, pill_y + 30, icon_text)

            # Gesture name
            raw_clean = self._gesture_raw.replace("_", " ").title()
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.setPen(col)
            painter.drawText(pill_x + 36, pill_y + 18, raw_clean)

            # Hand label (smaller)
            hand_label = ""
            if ": " in self._gesture_info:
                hand_label = self._gesture_info.split(": ")[0]
            painter.setFont(QFont("Arial", 7))
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(pill_x + 36, pill_y + 32, hand_label)

        # ── Active mode badge (top-center) ──
        if self._active_mode:
            mode_labels = {
                "zoom": ("🔍 ZOOM", QColor(255, 200, 50)),
                "select": ("📝 SELECCIÓN", QColor(180, 80, 255)),
                "dwell": ("⏳ DWELL", QColor(50, 200, 255)),
                "drag": ("✋ DRAG", QColor(255, 120, 50)),
                "scroll": ("📜 SCROLL", QColor(50, 255, 150)),
            }
            lbl, lbl_col = mode_labels.get(self._active_mode, (self._active_mode.upper(), QColor(255,255,255)))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            tw = painter.fontMetrics().horizontalAdvance(lbl) + 16
            mx = (self.frame_width - tw) // 2
            painter.setBrush(QBrush(QColor(0, 0, 0, 170)))
            painter.setPen(QPen(lbl_col, 1))
            painter.drawRoundedRect(mx, 4, tw, 22, 6, 6)
            painter.setPen(lbl_col)
            painter.drawText(mx + 8, 19, lbl)

        # ── Dwell-click progress ring ──
        if self._dwell_progress > 0.02:
            cx, cy, r = 30, self.frame_height - 30, 18
            # Background ring
            painter.setPen(QPen(QColor(60, 60, 60, 180), 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            # Progress arc
            pen = QPen(QColor(50, 220, 255), 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            span = int(-self._dwell_progress * 360 * 16)
            painter.drawArc(cx - r, cy - r, r * 2, r * 2, 90 * 16, span)
            # Center dot
            if self._dwell_progress >= 1.0:
                painter.setBrush(QBrush(QColor(50, 220, 255)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(cx - 5, cy - 5, 10, 10)

        # ── Log messages ──
        if self._log_messages:
            log_y = 56
            for msg in self._log_messages:
                painter.setPen(QColor(220, 220, 180))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(self.frame_width - 155, log_y, msg)
                log_y += 14

    def closeEvent(self, event):
        self._update_timer.stop()
        super().closeEvent(event)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGridLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QFont, QColor

import pyautogui


STYLE_KEY = """
    QPushButton {
        background-color: #2d2d2d;
        color: #f0f0f0;
        border: 1px solid #444;
        border-radius: 6px;
        font-size: 15px;
        font-weight: bold;
        padding: 4px;
    }
    QPushButton:hover {
        background-color: #3c3c3c;
        border: 1px solid #6a6a6a;
    }
    QPushButton:pressed {
        background-color: #555;
        color: #fff;
    }
"""

STYLE_SPECIAL = """
    QPushButton {
        background-color: #1a1a2e;
        color: #a0c4ff;
        border: 1px solid #333;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        padding: 4px;
    }
    QPushButton:hover {
        background-color: #16213e;
        border: 1px solid #6a9fd8;
    }
    QPushButton:pressed {
        background-color: #0f3460;
    }
"""

STYLE_BACKSPACE = """
    QPushButton {
        background-color: #3d1a1a;
        color: #ff8080;
        border: 1px solid #5a2a2a;
        border-radius: 6px;
        font-size: 14px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #5a2020;
    }
    QPushButton:pressed {
        background-color: #7a2020;
    }
"""

STYLE_SPACE = """
    QPushButton {
        background-color: #1e1e1e;
        color: #c0c0c0;
        border: 1px solid #555;
        border-radius: 6px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #2a2a2a;
    }
    QPushButton:pressed {
        background-color: #444;
    }
"""

STYLE_CLOSE = """
    QPushButton {
        background-color: #2a0a0a;
        color: #ff5555;
        border: 1px solid #5a1a1a;
        border-radius: 6px;
        font-size: 14px;
        font-weight: bold;
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
    }
    QPushButton:hover {
        background-color: #5a1a1a;
    }
    QPushButton:pressed {
        background-color: #7a0000;
    }
"""


class VirtualKeyboardWidget(QWidget):
    key_pressed = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⌨ Teclado Virtual — GestureOS")
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        # CRITICAL: never steal focus so pyautogui writes to the user's app
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 10px;")

        self._shift_active = False
        self._mode = "alpha"   # alpha | numbers

        self._setup_ui()
        self._position_bottom()

    def _position_bottom(self):
        """Place the keyboard at the bottom-center of the screen."""
        screen = self.screen().geometry()
        self.adjustSize()
        w = max(self.sizeHint().width(), 780)
        h = max(self.sizeHint().height(), 270)
        self.resize(w, h)
        x = (screen.width() - w) // 2
        y = screen.height() - h - 60
        self.move(x, y)

    # ------------------------------------------------------------------ UI --

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(6)

        # ── Title bar ──
        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("⌨ Teclado Virtual — GestureOS")
        lbl.setStyleSheet("color: #888; font-size: 11px;")
        title_bar.addWidget(lbl)
        title_bar.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setStyleSheet(STYLE_CLOSE)
        close_btn.setToolTip("Cerrar teclado")
        close_btn.clicked.connect(self._on_close)
        title_bar.addWidget(close_btn)

        outer.addLayout(title_bar)

        # ── Key grid ──
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        outer.addLayout(self.grid)

        self._build_alpha()

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    # ─────────────────────────── Alpha layout ─────────────────────────────

    def _build_alpha(self):
        self._clear_grid()
        self._mode = "alpha"

        row1 = list("qwertyuiop")
        row2 = list("asdfghjkl")
        row3 = list("zxcvbnm")

        def label(c):
            return c.upper() if self._shift_active else c

        # Row 0
        for i, c in enumerate(row1):
            self.grid.addWidget(self._mk_key(label(c), c), 0, i)

        # Row 1 (offset 0.5 visually — we can't do fractional cols in QGrid,
        # so span tricks are skipped; just left-align)
        for i, c in enumerate(row2):
            self.grid.addWidget(self._mk_key(label(c), c), 1, i)

        # Row 2 — shift + letters + backspace
        shift_btn = self._mk_special(
            "⇧ SHIFT" if not self._shift_active else "⇧ ON",
            self._toggle_shift
        )
        self.grid.addWidget(shift_btn, 2, 0, 1, 2)

        for i, c in enumerate(row3):
            self.grid.addWidget(self._mk_key(label(c), c), 2, i + 2)

        bksp = QPushButton("⌫")
        bksp.setFixedHeight(46)
        bksp.setStyleSheet(STYLE_BACKSPACE)
        bksp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bksp.clicked.connect(lambda: pyautogui.press("backspace"))
        self.grid.addWidget(bksp, 2, len(row3) + 2, 1, 2)

        # Row 3 — bottom bar
        num_btn = self._mk_special("123", lambda: self._build_numbers())
        self.grid.addWidget(num_btn, 3, 0, 1, 2)

        space = QPushButton("ESPACIO")
        space.setFixedHeight(46)
        space.setStyleSheet(STYLE_SPACE)
        space.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        space.clicked.connect(lambda: self._send(" "))
        self.grid.addWidget(space, 3, 2, 1, 5)

        enter = self._mk_special("↵ ENTER", lambda: pyautogui.press("enter"))
        self.grid.addWidget(enter, 3, 7, 1, 3)

    # ─────────────────────────── Numbers layout ────────────────────────────

    def _build_numbers(self):
        self._clear_grid()
        self._mode = "numbers"

        row1 = list("1234567890")
        row2 = ["-", "/", ":", ";", "(", ")", "$", "&", "@", "\""]
        row3 = [".", ",", "?", "!", "'"]

        for i, c in enumerate(row1):
            self.grid.addWidget(self._mk_key(c, c), 0, i)

        for i, c in enumerate(row2):
            self.grid.addWidget(self._mk_key(c, c), 1, i)

        abc = self._mk_special("ABC", lambda: self._build_alpha())
        self.grid.addWidget(abc, 2, 0, 1, 2)

        for i, c in enumerate(row3):
            self.grid.addWidget(self._mk_key(c, c), 2, i + 2)

        bksp2 = QPushButton("⌫")
        bksp2.setFixedHeight(46)
        bksp2.setStyleSheet(STYLE_BACKSPACE)
        bksp2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bksp2.clicked.connect(lambda: pyautogui.press("backspace"))
        self.grid.addWidget(bksp2, 2, len(row3) + 2, 1, 3)

        space2 = QPushButton("ESPACIO")
        space2.setFixedHeight(46)
        space2.setStyleSheet(STYLE_SPACE)
        space2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        space2.clicked.connect(lambda: self._send(" "))
        self.grid.addWidget(space2, 3, 0, 1, 6)

        enter2 = self._mk_special("↵ ENTER", lambda: pyautogui.press("enter"))
        self.grid.addWidget(enter2, 3, 6, 1, 4)

    # ─────────────────────────── Helpers ───────────────────────────────────

    def _mk_key(self, display: str, char: str) -> QPushButton:
        btn = QPushButton(display)
        btn.setFixedHeight(46)
        btn.setStyleSheet(STYLE_KEY)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda checked=False, c=char: self._on_key(c))
        return btn

    def _mk_special(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(46)
        btn.setStyleSheet(STYLE_SPECIAL)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(callback)
        return btn

    def _on_key(self, char: str):
        c = char.upper() if self._shift_active else char
        self._send(c)
        if self._shift_active:
            self._shift_active = False
            self._build_alpha()

    def _send(self, char: str):
        try:
            if len(char) == 1:
                pyautogui.write(char, interval=0.02)
            else:
                pyautogui.press(char)
        except Exception as e:
            print(f"[Keyboard] send error: {e}")
        self.key_pressed.emit(char)

    def _toggle_shift(self):
        self._shift_active = not self._shift_active
        self._build_alpha()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    # ─────────────────────────── Public API ────────────────────────────────

    @pyqtSlot()
    def show_keyboard(self):
        self._position_bottom()
        self.show()
        self.raise_()
        # Do NOT call activateWindow() — we must keep focus on the user's app

    @pyqtSlot()
    def hide_keyboard(self):
        self.hide()

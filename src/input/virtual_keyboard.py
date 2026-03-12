import time
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

import pyautogui

from src.core.config import KEYBOARD_LAYOUT, KEYBOARD_KEY_SIZE, KEYBOARD_KEY_SPACING
from src.core.gesture_recognizer import GestureType


class KeyboardMode(Enum):
    OFF = "off"
    ALPHABET = "alphabet"
    NUMBER = "number"
    SYMBOL = "symbol"
    NAVIGATION = "navigation"


@dataclass
class KeyData:
    key: str
    display: str
    x: int
    y: int
    width: int
    height: int
    is_special: bool = False
    action: Optional[str] = None


class VirtualKeyboard:
    def __init__(
        self,
        layout: str = KEYBOARD_LAYOUT,
        key_size: int = KEYBOARD_KEY_SIZE,
        spacing: int = KEYBOARD_KEY_SPACING
    ):
        self.layout = layout.lower()
        self.key_size = key_size
        self.spacing = spacing

        self.mode = KeyboardMode.OFF
        self.is_visible = False

        self._current_text = ""
        self._shift_active = False
        self._ctrl_active = False
        self._alt_active = False

        self._selected_key: Optional[KeyData] = None
        self._key_press_animation_time = 0
        self._key_press_animation_duration = 0.15

        self._pointer_position: Optional[Tuple[int, int]] = None

        self._keys: List[List[KeyData]] = []
        self._build_keyboards()

        self._last_key_press_time = 0
        self._key_cooldown = 0.2

        self._gesture_callback: Optional[Callable] = None

    def _build_keyboards(self):
        self._keyboard_layouts = {
            KeyboardMode.ALPHABET: self._build_alphabet_layout(),
            KeyboardMode.NUMBER: self._build_number_layout(),
            KeyboardMode.SYMBOL: self._build_symbol_layout(),
            KeyboardMode.NAVIGATION: self._build_navigation_layout()
        }

    def _build_alphabet_layout(self) -> List[List[KeyData]]:
        rows = []
        y = 0

        row1 = "qwertyuiop"
        row2 = "asdfghjkl"
        row3 = "zxcvbnm"

        for row_str in [row1, row2, row3]:
            row_keys = []
            x = 0
            for char in row_str:
                row_keys.append(KeyData(
                    key=char,
                    display=char.upper() if self._shift_active else char,
                    x=x,
                    y=y,
                    width=self.key_size,
                    height=self.key_size
                ))
                x += self.key_size + self.spacing
            rows.append(row_keys)
            y += self.key_size + self.spacing

        row_y = y
        special_keys = [
            ("shift", "⇧", True, "toggle_shift"),
            ("space", "espacio", True, "space"),
            ("enter", "↵", True, "enter"),
            ("123", "123", True, "mode_number"),
            ("abc", "abc", True, "mode_symbol")
        ]

        special_row = []
        x = 0
        for key, display, _, action in special_keys:
            width = self.key_size * 3 if key == "space" else self.key_size
            special_row.append(KeyData(
                key=key,
                display=display,
                x=x,
                y=row_y,
                width=width,
                height=self.key_size,
                is_special=True,
                action=action
            ))
            x += width + self.spacing

        rows.append(special_row)

        return rows

    def _build_number_layout(self) -> List[List[KeyData]]:
        rows = []
        y = 0

        numbers = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            ["-", "/", ":", ";", "(", ")", "$", "&", "@", "\""],
            [".", ",", "?", "!", "'"]
        ]

        for row_str in numbers:
            row_keys = []
            x = 0
            for char in row_str:
                row_keys.append(KeyData(
                    key=char,
                    display=char,
                    x=x,
                    y=y,
                    width=self.key_size,
                    height=self.key_size
                ))
                x += self.key_size + self.spacing
            rows.append(row_keys)
            y += self.key_size + self.spacing

        special_row = []
        x = 0
        special_keys = [
            ("#+=t", "#+=", True, "mode_symbol"),
            ("space", "espacio", True, "space"),
            ("abc", "abc", True, "mode_alphabet")
        ]
        for key, display, _, action in special_keys:
            width = self.key_size * 3 if key == "space" else self.key_size * 2
            special_row.append(KeyData(
                key=key,
                display=display,
                x=x,
                y=y,
                width=width,
                height=self.key_size,
                is_special=True,
                action=action
            ))
            x += width + self.spacing

        rows.append(special_row)

        return rows

    def _build_symbol_layout(self) -> List[List[KeyData]]:
        rows = []
        y = 0

        symbols = [
            ["[", "]", "{", "}", "#", "%", "^", "*", "+", "="],
            ["_", "\\", "|", "~", "<", ">", "€", "£", "¥", "•"],
            [".", ",", "?", "!", "'"]
        ]

        for row_str in symbols:
            row_keys = []
            x = 0
            for char in row_str:
                row_keys.append(KeyData(
                    key=char,
                    display=char,
                    x=x,
                    y=y,
                    width=self.key_size,
                    height=self.key_size
                ))
                x += self.key_size + self.spacing
            rows.append(row_keys)
            y += self.key_size + self.spacing

        special_row = []
        x = 0
        special_keys = [
            ("123", "123", True, "mode_number"),
            ("space", "espacio", True, "space"),
            ("abc", "abc", True, "mode_alphabet")
        ]
        for key, display, _, action in special_keys:
            width = self.key_size * 3 if key == "space" else self.key_size * 2
            special_row.append(KeyData(
                key=key,
                display=display,
                x=x,
                y=y,
                width=width,
                height=self.key_size,
                is_special=True,
                action=action
            ))
            x += width + self.spacing

        rows.append(special_row)

        return rows

    def _build_navigation_layout(self) -> List[List[KeyData]]:
        return []

    def toggle(self):
        if self.mode == KeyboardMode.OFF:
            self.mode = KeyboardMode.ALPHABET
            self.is_visible = True
        else:
            self.mode = KeyboardMode.OFF
            self.is_visible = False

    def show(self):
        self.mode = KeyboardMode.ALPHABET
        self.is_visible = True

    def hide(self):
        self.mode = KeyboardMode.OFF
        self.is_visible = False

    def update_pointer(self, position: Tuple[int, int]):
        self._pointer_position = position

    def handle_gesture(self, gesture: GestureType, hand_position: Tuple[int, int]):
        if not self.is_visible or self.mode == KeyboardMode.OFF:
            return

        self.update_pointer(hand_position)

        current_time = time.time()

        if gesture == GestureType.PINCH or gesture == GestureType.OK_SIGN:
            if current_time - self._last_key_press_time >= self._key_cooldown:
                key = self._get_key_at_position(hand_position)
                if key:
                    self._press_key(key)
                    self._last_key_press_time = current_time

    def _get_key_at_position(self, position: Tuple[int, int]) -> Optional[KeyData]:
        for row in self._keyboard_layouts.get(self.mode, []):
            for key in row:
                if (key.x <= position[0] <= key.x + key.width and
                    key.y <= position[1] <= key.y + key.height):
                    return key
        return None

    def _press_key(self, key: KeyData):
        self._selected_key = key
        self._key_press_animation_time = time.time()

        if key.is_special:
            self._handle_special_key(key)
        else:
            char = key.key
            if self._shift_active:
                char = char.upper()
            self._type_character(char)

        if self._gesture_callback:
            self._gesture_callback(key.key)

    def _handle_special_key(self, key: KeyData):
        if key.action == "toggle_shift":
            self._shift_active = not self._shift_active
            self._build_keyboards()
        elif key.action == "space":
            self._type_character(" ")
        elif key.action == "enter":
            pyautogui.press("enter")
        elif key.action == "backspace":
            pyautogui.press("backspace")
        elif key.action == "mode_number":
            self.mode = KeyboardMode.NUMBER
            self._build_keyboards()
        elif key.action == "mode_symbol":
            self.mode = KeyboardMode.SYMBOL
            self._build_keyboards()
        elif key.action == "mode_alphabet":
            self.mode = KeyboardMode.ALPHABET
            self._build_keyboards()
        elif key.action == "tab":
            pyautogui.press("tab")
        elif key.action == "escape":
            pyautogui.press("escape")

    def _type_character(self, char: str):
        try:
            pyautogui.write(char, _pause=False)
        except Exception:
            pass

    def set_gesture_callback(self, callback: Callable):
        self._gesture_callback = callback

    def get_keyboard_layout(self) -> List[List[KeyData]]:
        return self._keyboard_layouts.get(self.mode, [])

    def get_mode(self) -> KeyboardMode:
        return self.mode

    def is_shift_active(self) -> bool:
        return self._shift_active

    def get_current_text(self) -> str:
        return self._current_text

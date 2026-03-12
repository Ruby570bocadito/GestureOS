import time
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass

import pyautogui
import psutil
from pathlib import Path

from src.core.config import SCREENSHOT_DIR


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    process_name: str
    is_active: bool


class SystemController:
    def __init__(self):
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0

        self._hotkey_handlers: Dict[str, Callable] = {}

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left"):
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button, _pause=False)
        else:
            pyautogui.click(button=button, _pause=False)

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        self.click(x, y, button="right")

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        if x is not None and y is not None:
            pyautogui.doubleClick(x, y, _pause=False)
        else:
            pyautogui.doubleClick(_pause=False)

    def move_to(self, x: int, y: int):
        pyautogui.moveTo(x, y, _pause=False)

    def drag_to(self, x: int, y: int, duration: float = 0.5):
        pyautogui.dragTo(x, y, duration=duration, _pause=False)

    def scroll(self, amount: int):
        pyautogui.scroll(amount, _pause=False)

    def write(self, text: str):
        pyautogui.write(text, _pause=False)

    def press(self, key: str):
        pyautogui.press(key, _pause=False)

    def hotkey(self, *keys):
        pyautogui.hotkey(*keys, _pause=False)

    def get_screen_size(self) -> tuple:
        return pyautogui.size()

    def get_mouse_position(self) -> tuple:
        return pyautogui.position()

    def take_screenshot(self, filename: Optional[str] = None) -> Path:
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        filepath = SCREENSHOT_DIR / filename

        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)

        return filepath

    def minimize_window(self):
        pyautogui.hotkey("win", "down", _pause=False)

    def maximize_window(self):
        pyautogui.hotkey("win", "up", _pause=False)

    def close_window(self):
        pyautogui.hotkey("alt", "f4", _pause=False)

    def switch_window(self):
        pyautogui.hotkey("alt", "tab", _pause=False)

    def new_window(self):
        pyautogui.hotkey("ctrl", "n", _pause=False)

    def open_task_view(self):
        pyautogui.hotkey("win", "tab", _pause=False)

    def volume_up(self, times: int = 1):
        for _ in range(times):
            pyautogui.press("volumeup", _pause=False)

    def volume_down(self, times: int = 1):
        for _ in range(times):
            pyautogui.press("volumedown", _pause=False)

    def mute_volume(self):
        pyautogui.press("volumemute", _pause=False)

    def get_active_window(self) -> Optional[WindowInfo]:
        try:
            import win32gui
            import win32process

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name()

            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                is_active=True
            )

        except Exception:
            return None

    def get_open_windows(self) -> List[WindowInfo]:
        windows = []

        try:
            import win32gui
            import win32process

            def callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            process = psutil.Process(pid)
                            process_name = process.name()

                            windows.append(WindowInfo(
                                hwnd=hwnd,
                                title=title,
                                process_name=process_name,
                                is_active=False
                            ))
                        except Exception:
                            pass
                return True

            win32gui.EnumWindows(callback, None)

        except Exception:
            pass

        return windows

    def open_application(self, app_name: str) -> bool:
        try:
            pyautogui.press("win", _pause=False)
            time.sleep(0.3)
            pyautogui.write(app_name, _pause=False)
            time.sleep(0.3)
            pyautogui.press("enter", _pause=False)
            return True
        except Exception:
            return False

    def register_hotkey(self, key_combo: str, handler: Callable):
        self._hotkey_handlers[key_combo] = handler

    def unregister_hotkey(self, key_combo: str):
        self._hotkey_handlers.pop(key_combo, None)

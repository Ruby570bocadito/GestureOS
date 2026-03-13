import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

MEDIAPIPE_MAX_HANDS = 2
MEDIAPIPE_MODEL_COMPLEXITY = 1
MEDIAPIPE_DETECTION_CONFIDENCE = 0.8
MEDIAPIPE_TRACKING_CONFIDENCE = 0.7

MOUSE_SMOOTHING = 0.30          # 0=none 1=max lag — higher = more responsive
MOUSE_SPEED_MULTIPLIER = 2.2    # higher = faster cursor
MOUSE_DEADZONE = 8              # pixels of deadzone (smaller = more precise)

CLICK_GESTURE = "thumbs_up"
RIGHT_CLICK_GESTURE = "thumbs_down"
SCROLL_GESTURE = "pointing_up"
DRAG_GESTURE = "thumbs_up"

OLLAMA_MODEL = "llama3:8b"
OLLAMA_VISION_MODEL = "llama3:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

VOICE_LANGUAGE = "es"
VOICE_RATE = 150
VOICE_VOLUME = 1.0

OVERLAY_OPACITY = 0.85
OVERLAY_FPS = 30
OVERLAY_CAMERA_WIDTH = 480
OVERLAY_CAMERA_HEIGHT = 360

KEYBOARD_LAYOUT = "qwerty"
KEYBOARD_KEY_SIZE = 50
KEYBOARD_KEY_SPACING = 5

GESTURES = {
    "open_palm": "stop_drag",
    "fist": "grab",
    "pointing_up": "scroll_mode",
    "peace": "right_click",
    "thumbs_up": "confirm",
    "thumbs_down": "cancel",
    "ok_sign": "click",
    "pinch": "click",
    "two_finger_tap": "right_click",
    "three_finger_tap": "middle_click",
    "swipe_left": "prev",
    "swipe_right": "next",
    "swipe_up": "volume_up",
    "swipe_down": "volume_down",
}

SCREENSHOT_DIR = BASE_DIR / "screenshots"
LOG_DIR = BASE_DIR / "logs"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

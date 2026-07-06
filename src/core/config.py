import os
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

# ── Logging ──
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "handscontrol.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("handscontrol")

# ── MediaPipe ──
MEDIAPIPE_MAX_HANDS = 2
MEDIAPIPE_MODEL_COMPLEXITY = 1
MEDIAPIPE_DETECTION_CONFIDENCE = 0.8
MEDIAPIPE_TRACKING_CONFIDENCE = 0.7

# ── Mouse ──
MOUSE_SMOOTHING = 0.30
MOUSE_SPEED_MULTIPLIER = 2.2
MOUSE_DEADZONE = 8

MOUSE_SPEED_MAP = {1: 0.9, 2: 1.5, 3: 2.2, 4: 3.2, 5: 4.5}
MOUSE_SMOOTHING_MAP = {1: 0.12, 2: 0.20, 3: 0.30, 4: 0.40, 5: 0.55}

CLICK_COOLDOWN = 0.45
SCROLL_COOLDOWN = 0.08
DWELL_THRESHOLD = 1.5
DWELL_DEADZONE = 25

ZOOM_DELTA_THRESHOLD = 10
ZOOM_SCROLL_DIVISOR = 15
SCROLL_UNITS_DIVISOR = 8

# ── Gestures ──
CLICK_GESTURE = "thumbs_up"
RIGHT_CLICK_GESTURE = "thumbs_down"
SCROLL_GESTURE = "pointing_up"
DRAG_GESTURE = "thumbs_up"

GESTURE_SWIPE_THRESHOLD = 50
GESTURE_SWIPE_VELOCITY_THRESHOLD = 0.5
GESTURE_POSITION_HISTORY_MAX = 15
GESTURE_HISTORY_MAX = 10
GESTURE_FINGER_EXTENDED_RATIO = 0.6
GESTURE_THUMB_EXTENDED_RATIO = 0.4
GESTURE_OK_DISTANCE = 0.05
GESTURE_PINCH_DISTANCE = 0.07
GESTURE_BASE_CONFIDENCE = 0.7
GESTURE_CONFIDENCE_BONUS = 0.2

# ── Shortcuts ──
SHORTCUT_COOLDOWN = 1.5
SHORTCUT_COMBO_WINDOW = 0.8

# ── Keyboard toggle ──
KEYBOARD_TOGGLE_COOLDOWN = 3.0

# ── Duplicate hand detection ──
HAND_DUPLICATE_THRESHOLD = 50

# ── Ollama / AI ──
OLLAMA_MODEL = "llama3:8b"
OLLAMA_VISION_MODEL = "llama3:8b"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TEMPERATURE = 0.3
OLLAMA_NUM_PREDICT = 500
OLLAMA_VISION_NUM_PREDICT = 300
OLLAMA_ASK_TIMEOUT = 30
MAX_CONVERSATION_LENGTH = 50

# ── Voice ──
VOICE_LANGUAGE = "es"
VOICE_RATE = 150
VOICE_VOLUME = 1.0
VOICE_ENERGY_THRESHOLD = 300
VOICE_PAUSE_THRESHOLD = 0.6
VOICE_COMMAND_COOLDOWN = 2.0
VOICE_LISTEN_TIMEOUT = 4
VOICE_PHRASE_TIME_LIMIT = 6
VOICE_CALIBRATION_DURATION = 0.8
VOICE_PRE_SPEAK_DELAY = 0.3
VOICE_POST_SPEAK_DELAY = 0.5
VOICE_AGENT_SPEAK_DELAY = 0.5
VOICE_AGENT_SPEAK_MAX_LEN = 150

# ── Overlay ──
OVERLAY_OPACITY = 0.85
OVERLAY_FPS = 30
OVERLAY_CAMERA_WIDTH = 480
OVERLAY_CAMERA_HEIGHT = 360
OVERLAY_UPDATE_INTERVAL_MS = 33
OVERLAY_BAR_HEIGHT = 56
OVERLAY_PILL_WIDTH = 110
OVERLAY_PILL_HEIGHT = 44
OVERLAY_DWELL_RING_RADIUS = 18
OVERLAY_MAX_LOG_MESSAGES = 4
OVERLAY_FPS_ACCUMULATOR_MAX = 15
OVERLAY_FPS_UPDATE_INTERVAL = 0.5
OVERLAY_TIMESTAMP_INCREMENT = 33.33

# ── Keyboard ──
KEYBOARD_LAYOUT = "qwerty"
KEYBOARD_KEY_SIZE = 50
KEYBOARD_KEY_SPACING = 5
KEY_COOLDOWN = 0.2
KEY_PRESS_ANIMATION_DURATION = 0.15

# ── Capture loop ──
CAPTURE_FRAME_WIDTH = 640
CAPTURE_FRAME_HEIGHT = 480
CAPTURE_FPS = 30
CAPTURE_READ_RETRY_SLEEP = 0.01
CAPTURE_ERROR_SLEEP = 0.1
CAPTURE_STOP_SLEEP = 0.5

# ── Vision ──
VISION_RESIZE_FACTOR = 2
VISION_SCREENSHOT_FILENAME = "temp_screenshot.png"

# ── Action Executor ──
ACTION_EXECUTOR_PAUSE = 0.05
ACTION_EXECUTOR_WRITE_INTERVAL = 0.03
ACTION_CLOSE_WINDOW_DELAY = 0.2
ACTION_VOLUME_STEPS = 5

# ── Directories ──
SCREENSHOT_DIR = BASE_DIR / "screenshots"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ── Gesture-action mapping ──
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

"""Tests for HandsControl config module."""

import pytest
from src.core.config import (
    MOUSE_SMOOTHING,
    MOUSE_SPEED_MULTIPLIER,
    MOUSE_DEADZONE,
    CLICK_COOLDOWN,
    SCROLL_COOLDOWN,
    DWELL_THRESHOLD,
    KEYBOARD_TOGGLE_COOLDOWN,
    SHORTCUT_COOLDOWN,
    SHORTCUT_COMBO_WINDOW,
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_TEMPERATURE,
    VOICE_LANGUAGE,
    VOICE_ENERGY_THRESHOLD,
    VOICE_COMMAND_COOLDOWN,
    MEDIAPIPE_DETECTION_CONFIDENCE,
    MEDIAPIPE_TRACKING_CONFIDENCE,
    OVERLAY_OPACITY,
    OVERLAY_FPS,
    CAPTURE_FRAME_WIDTH,
    CAPTURE_FRAME_HEIGHT,
    CAPTURE_FPS,
    GESTURES,
    MOUSE_SPEED_MAP,
    MOUSE_SMOOTHING_MAP,
    BASE_DIR,
    LOG_DIR,
)


class TestMouseConfig:
    def test_smoothing_in_range(self):
        assert 0.0 < MOUSE_SMOOTHING <= 1.0

    def test_speed_multiplier_positive(self):
        assert MOUSE_SPEED_MULTIPLIER > 0

    def test_deadzone_positive(self):
        assert MOUSE_DEADZONE >= 0

    def test_click_cooldown_positive(self):
        assert CLICK_COOLDOWN > 0

    def test_scroll_cooldown_positive(self):
        assert SCROLL_COOLDOWN > 0

    def test_dwell_threshold_positive(self):
        assert DWELL_THRESHOLD > 0

    def test_speed_map_has_five_levels(self):
        assert len(MOUSE_SPEED_MAP) == 5
        for level in range(1, 6):
            assert level in MOUSE_SPEED_MAP

    def test_smoothing_map_has_five_levels(self):
        assert len(MOUSE_SMOOTHING_MAP) == 5
        for level in range(1, 6):
            assert level in MOUSE_SMOOTHING_MAP


class TestKeyboardConfig:
    def test_keyboard_toggle_cooldown_positive(self):
        assert KEYBOARD_TOGGLE_COOLDOWN > 0


class TestShortcutConfig:
    def test_shortcut_cooldown_positive(self):
        assert SHORTCUT_COOLDOWN > 0

    def test_combo_window_positive(self):
        assert SHORTCUT_COMBO_WINDOW > 0


class TestOllamaConfig:
    def test_model_not_empty(self):
        assert len(OLLAMA_MODEL) > 0

    def test_base_url_valid(self):
        assert OLLAMA_BASE_URL.startswith("http")

    def test_temperature_in_range(self):
        assert 0.0 <= OLLAMA_TEMPERATURE <= 2.0


class TestVoiceConfig:
    def test_language_is_es(self):
        assert VOICE_LANGUAGE == "es"

    def test_energy_threshold_positive(self):
        assert VOICE_ENERGY_THRESHOLD > 0

    def test_command_cooldown_positive(self):
        assert VOICE_COMMAND_COOLDOWN > 0


class TestMediaPipeConfig:
    def test_detection_confidence_in_range(self):
        assert 0.0 <= MEDIAPIPE_DETECTION_CONFIDENCE <= 1.0

    def test_tracking_confidence_in_range(self):
        assert 0.0 <= MEDIAPIPE_TRACKING_CONFIDENCE <= 1.0


class TestOverlayConfig:
    def test_opacity_in_range(self):
        assert 0.0 <= OVERLAY_OPACITY <= 1.0

    def test_fps_positive(self):
        assert OVERLAY_FPS > 0


class TestCaptureConfig:
    def test_frame_width_positive(self):
        assert CAPTURE_FRAME_WIDTH > 0

    def test_frame_height_positive(self):
        assert CAPTURE_FRAME_HEIGHT > 0

    def test_fps_positive(self):
        assert CAPTURE_FPS > 0


class TestGesturesMapping:
    def test_gestures_dict_not_empty(self):
        assert len(GESTURES) > 0

    def test_known_gestures(self):
        expected = ["open_palm", "fist", "thumbs_up", "thumbs_down", "peace", "ok_sign", "pinch"]
        for gesture in expected:
            assert gesture in GESTURES


class TestDirectories:
    def test_base_dir_exists(self):
        assert BASE_DIR.is_dir()

    def test_log_dir_created(self):
        assert LOG_DIR.is_dir()

"""Tests for HandsControl gesture recognizer."""

import numpy as np
import pytest
from src.core.gesture_recognizer import (
    GestureType,
    GestureState,
)


class TestGestureType:
    def test_all_gestures_have_values(self):
        for gesture in GestureType:
            assert len(gesture.value) > 0

    def test_open_palm(self):
        assert GestureType.OPEN_PALM.value == "open_palm"

    def test_fist(self):
        assert GestureType.FIST.value == "fist"

    def test_thumbs_up(self):
        assert GestureType.THUMBS_UP.value == "thumbs_up"

    def test_thumbs_down(self):
        assert GestureType.THUMBS_DOWN.value == "thumbs_down"

    def test_peace(self):
        assert GestureType.PEACE.value == "peace"

    def test_pinch(self):
        assert GestureType.PINCH.value == "pinch"

    def test_unknown(self):
        assert GestureType.UNKNOWN.value == "unknown"

    def test_from_string_valid(self):
        assert GestureType("fist") == GestureType.FIST

    def test_from_string_invalid(self):
        with pytest.raises(ValueError):
            GestureType("invalid_gesture")


class TestGestureState:
    def test_creation(self):
        state = GestureState(
            gesture=GestureType.OPEN_PALM,
            confidence=0.95,
            hand_position=(320, 240),
            finger_states={"index": True, "thumb": False},
        )
        assert state.gesture == GestureType.OPEN_PALM
        assert state.confidence == 0.95
        assert state.hand_position == (320, 240)


class TestGestureRecognizer:
    """Tests that require mediapipe."""

    @pytest.fixture(autouse=True)
    def _ensure_mediapipe(self):
        try:
            from src.core.gesture_recognizer import GestureRecognizer
            from src.core.gesture_tracker import HandData
            rec = GestureRecognizer()
            hand = HandData(
                hand_id=0, landmarks=np.zeros((21, 3)),
                landmarks_2d=np.zeros((21, 2)),
                handedness="Right", landmarks_visibility=np.ones(21),
                palm_center=(0, 0), palm_normal=np.array([0, 0, 1]),
            )
            rec.recognize(hand)
        except OSError:
            pytest.skip("mediapipe requires missing system libraries (libGLESv2)")

    def test_create(self):
        from src.core.gesture_recognizer import GestureRecognizer
        recognizer = GestureRecognizer()
        assert recognizer is not None

    def test_recognize_returns_gesture_state(self):
        from src.core.gesture_recognizer import GestureRecognizer
        from src.core.gesture_tracker import HandData

        recognizer = GestureRecognizer()
        hand = HandData(
            hand_id=0, landmarks=np.zeros((21, 3)),
            landmarks_2d=np.zeros((21, 2)),
            handedness="Right", landmarks_visibility=np.ones(21),
            palm_center=(320, 240), palm_normal=np.array([0, 0, 1]),
        )
        state = recognizer.recognize(hand)
        assert state.confidence >= 0.0

    def test_gesture_history_updated(self):
        from src.core.gesture_recognizer import GestureRecognizer
        from src.core.gesture_tracker import HandData

        recognizer = GestureRecognizer()
        hand = HandData(
            hand_id=0, landmarks=np.zeros((21, 3)),
            landmarks_2d=np.zeros((21, 2)),
            handedness="Right", landmarks_visibility=np.ones(21),
            palm_center=(320, 240), palm_normal=np.array([0, 0, 1]),
        )
        for _ in range(5):
            recognizer.recognize(hand)
        assert len(recognizer.history) > 0

    def test_recognize_multiple_times(self):
        from src.core.gesture_recognizer import GestureRecognizer
        from src.core.gesture_tracker import HandData

        recognizer = GestureRecognizer()
        hand = HandData(
            hand_id=0, landmarks=np.zeros((21, 3)),
            landmarks_2d=np.zeros((21, 2)),
            handedness="Right", landmarks_visibility=np.ones(21),
            palm_center=(320, 240), palm_normal=np.array([0, 0, 1]),
        )
        for _ in range(15):
            state = recognizer.recognize(hand)
            assert isinstance(state, GestureState)

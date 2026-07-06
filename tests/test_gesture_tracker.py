"""Tests for HandsControl gesture tracker."""

import numpy as np
import pytest


class TestHandData:
    def test_creation(self):
        from src.core.gesture_tracker import HandData

        hand = HandData(
            hand_id=0,
            landmarks=np.zeros((21, 3)),
            landmarks_2d=np.zeros((21, 2)),
            handedness="Right",
            landmarks_visibility=np.ones(21),
            palm_center=(320, 240),
            palm_normal=np.array([0, 0, 1]),
        )
        assert hand.hand_id == 0
        assert hand.handedness == "Right"
        assert hand.palm_center == (320, 240)

    def test_left_hand(self):
        from src.core.gesture_tracker import HandData

        hand = HandData(
            hand_id=1,
            landmarks=np.zeros((21, 3)),
            landmarks_2d=np.zeros((21, 2)),
            handedness="Left",
            landmarks_visibility=np.ones(21),
            palm_center=(100, 200),
            palm_normal=np.array([0, 0, 1]),
        )
        assert hand.handedness == "Left"


class TestGestureTracker:
    """Tests that require mediapipe."""

    @pytest.fixture(autouse=True)
    def _ensure_mediapipe(self):
        try:
            from src.core.gesture_tracker import GestureTracker
            tracker = GestureTracker()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            tracker.process_frame(frame)
        except OSError:
            pytest.skip("mediapipe requires missing system libraries (libGLESv2)")

    def test_create_without_task_file(self):
        from src.core.gesture_tracker import GestureTracker
        tracker = GestureTracker()
        assert tracker is not None

    def test_fps_initial_value(self):
        from src.core.gesture_tracker import GestureTracker
        tracker = GestureTracker()
        assert tracker.fps >= 0

    def test_process_empty_frame(self):
        from src.core.gesture_tracker import GestureTracker
        tracker = GestureTracker()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hands = tracker.process_frame(frame)
        assert isinstance(hands, list)

    def test_release(self):
        from src.core.gesture_tracker import GestureTracker
        tracker = GestureTracker()
        tracker.release()

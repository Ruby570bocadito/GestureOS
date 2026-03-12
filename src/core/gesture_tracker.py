import cv2
import numpy as np
import time
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

from mediapipe import Image, ImageFormat
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerResult
from mediapipe.tasks.python.vision import drawing_utils

from src.core.config import (
    MEDIAPIPE_MAX_HANDS,
    MEDIAPIPE_MODEL_COMPLEXITY,
    MEDIAPIPE_DETECTION_CONFIDENCE,
    MEDIAPIPE_TRACKING_CONFIDENCE,
    OVERLAY_CAMERA_WIDTH,
    OVERLAY_CAMERA_HEIGHT
)


@dataclass
class HandData:
    hand_id: int
    landmarks: np.ndarray
    landmarks_2d: np.ndarray
    handedness: str
    landmarks_visibility: np.ndarray
    palm_center: Tuple[int, int]
    palm_normal: np.ndarray


class GestureTracker:
    def __init__(
        self,
        max_hands: int = MEDIAPIPE_MAX_HANDS,
        model_complexity: int = MEDIAPIPE_MODEL_COMPLEXITY,
        detection_confidence: float = MEDIAPIPE_DETECTION_CONFIDENCE,
        tracking_confidence: float = MEDIAPIPE_TRACKING_CONFIDENCE
    ):
        self.max_hands = max_hands
        self.model_complexity = model_complexity
        self.detection_confidence = detection_confidence
        self.tracking_confidence = tracking_confidence

        base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        
        try:
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=max_hands,
                running_mode=vision.RunningMode.VIDEO,
                min_hand_detection_confidence=detection_confidence,
                min_hand_presence_confidence=tracking_confidence,
                min_tracking_confidence=tracking_confidence
            )
            self.landmarker = HandLandmarker.create_from_options(options)
            print("Using GPU for hand tracking")
        except Exception as e:
            print(f"Using CPU: {e}")
            base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=max_hands,
                running_mode=vision.RunningMode.VIDEO,
                min_hand_detection_confidence=detection_confidence,
                min_hand_presence_confidence=tracking_confidence,
                min_tracking_confidence=tracking_confidence
            )
            self.landmarker = HandLandmarker.create_from_options(options)

        self.mp_drawing = drawing_utils
        self.mp_drawing_styles = None

        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = 0
        self._fps_accumulator = []
        self._last_frame_time = time.time()

    def process_frame(self, frame: np.ndarray) -> List[HandData]:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=frame_rgb)

        timestamp_ms = int(self.frame_count * 33.33)
        result = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        hands_data = []
        if result.hand_landmarks and result.handedness:
            for idx, (landmarks, handedness) in enumerate(zip(
                result.hand_landmarks,
                result.handedness
            )):
                hand_data = self._extract_hand_data(landmarks, handedness, idx)
                hands_data.append(hand_data)

        self.frame_count += 1
        self._update_fps()
        return hands_data

    def _extract_hand_data(self, landmarks, handedness, hand_id: int) -> HandData:
        points_3d = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        points_2d = np.array([[lm.x, lm.y] for lm in landmarks])
        visibility = np.array([lm.visibility for lm in landmarks])

        palm_center_idx = 9
        palm_center = (
            int(landmarks[palm_center_idx].x * OVERLAY_CAMERA_WIDTH),
            int(landmarks[palm_center_idx].y * OVERLAY_CAMERA_HEIGHT)
        )

        wrist = points_3d[0]
        middle_mcp = points_3d[9]
        index_mcp = points_3d[5]
        palm_normal = np.cross(
            middle_mcp - wrist,
            index_mcp - wrist
        )
        if np.linalg.norm(palm_normal) > 0:
            palm_normal = palm_normal / np.linalg.norm(palm_normal)

        handedness_label = handedness[0].category_name if handedness else "Unknown"

        return HandData(
            hand_id=hand_id,
            landmarks=points_3d,
            landmarks_2d=points_2d,
            handedness=handedness_label,
            landmarks_visibility=visibility,
            palm_center=palm_center,
            palm_normal=palm_normal
        )

    def _update_fps(self):
        current_time = time.time()

        if self._last_frame_time == 0:
            self._last_frame_time = current_time
            return

        elapsed = current_time - self._last_frame_time
        if elapsed > 0:
            self._fps_accumulator.append(1 / elapsed)

        if len(self._fps_accumulator) > 15:
            self._fps_accumulator.pop(0)

        if current_time - self.last_fps_time >= 0.5:
            self.fps = int(np.mean(self._fps_accumulator)) if self._fps_accumulator else 0
            self.last_fps_time = current_time

        self._last_frame_time = current_time

    def draw_landmarks(self, frame: np.ndarray, hand_data: HandData) -> np.ndarray:
        h, w = frame.shape[:2]

        for i, landmark in enumerate(hand_data.landmarks_2d):
            x = int(landmark[0] * w)
            y = int(landmark[1] * h)
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

        return frame

    def get_hand_position(self, hand_data: HandData, landmark_idx: int) -> Tuple[int, int]:
        landmark = hand_data.landmarks_2d[landmark_idx]
        x = int(landmark[0] * OVERLAY_CAMERA_WIDTH)
        y = int(landmark[1] * OVERLAY_CAMERA_HEIGHT)
        return (x, y)

    def get_finger_states(self, hand_data: HandData) -> Dict[str, bool]:
        landmarks = hand_data.landmarks_2d

        states = {}

        states['thumb'] = self._is_finger_extended(landmarks, 1, 2, 3, 4)
        states['index'] = self._is_finger_extended(landmarks, 5, 6, 7, 8)
        states['middle'] = self._is_finger_extended(landmarks, 9, 10, 11, 12)
        states['ring'] = self._is_finger_extended(landmarks, 13, 14, 15, 16)
        states['pinky'] = self._is_finger_extended(landmarks, 17, 18, 19, 20)

        return states

    def _is_finger_extended(self, landmarks, base_idx, idx1, idx2, tip_idx) -> bool:
        base = landmarks[base_idx]
        tip = landmarks[tip_idx]
        mcp = landmarks[base_idx - 1]

        finger_length = np.linalg.norm(tip - base)
        palm_width = np.linalg.norm(landmarks[0] - landmarks[9])

        extended = finger_length > palm_width * 0.5
        return extended

    def release(self):
        self.landmarker.close()

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.core.gesture_tracker import HandData


class GestureType(Enum):
    UNKNOWN = "unknown"
    OPEN_PALM = "open_palm"
    FIST = "fist"
    POINTING_UP = "pointing_up"
    PEACE = "peace"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    OK_SIGN = "ok_sign"
    PINCH = "pinch"
    TWO_FINGER_TAP = "two_finger_tap"
    THREE_FINGER_TAP = "three_finger_tap"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    ONE_FINGER = "one_finger"
    TWO_FINGER_SCROLL = "two_finger_scroll"
    INDEX_CLICK = "index_click"   # index closed, rest extended = wink click


@dataclass
class GestureState:
    gesture: GestureType
    confidence: float
    hand_position: Tuple[int, int]
    finger_states: Dict[str, bool]


class GestureRecognizer:
    def __init__(self):
        self.history: List[GestureState] = []
        self.max_history = 10
        self.swipe_threshold = 50
        self.swipe_velocity_threshold = 0.5

        self._position_history: Dict[int, List[Tuple[int, int]]] = {}
        self._position_history_max = 15

    def recognize(self, hand_data: HandData) -> GestureState:
        finger_states = self._get_finger_states(hand_data)
        hand_pos = hand_data.palm_center

        gesture = self._classify_gesture(finger_states, hand_data)

        confidence = self._calculate_confidence(finger_states, gesture)

        state = GestureState(
            gesture=gesture,
            confidence=confidence,
            hand_position=hand_pos,
            finger_states=finger_states
        )

        self._update_position_history(hand_data.hand_id, hand_pos)
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        return state

    def _get_finger_states(self, hand_data: HandData) -> Dict[str, bool]:
        landmarks = hand_data.landmarks_2d
        landmarks_3d = hand_data.landmarks

        thumb_extended = self._is_thumb_extended(landmarks, landmarks_3d)
        index_extended = self._is_finger_extended(landmarks, 5, 6, 7, 8)
        middle_extended = self._is_finger_extended(landmarks, 9, 10, 11, 12)
        ring_extended = self._is_finger_extended(landmarks, 13, 14, 15, 16)
        pinky_extended = self._is_finger_extended(landmarks, 17, 18, 19, 20)

        return {
            'thumb': thumb_extended,
            'index': index_extended,
            'middle': middle_extended,
            'ring': ring_extended,
            'pinky': pinky_extended
        }

    def _is_finger_extended(self, landmarks, base_idx, idx1, idx2, tip_idx) -> bool:
        base = landmarks[base_idx]
        tip = landmarks[tip_idx]
        mcp = landmarks[base_idx - 1]

        base_to_tip = tip - base
        base_to_mcp = mcp - base

        finger_length = np.linalg.norm(base_to_tip)
        palm_diag = np.linalg.norm(landmarks[0] - landmarks[9])

        extended = finger_length > palm_diag * 0.6

        return extended

    def _is_thumb_extended(self, landmarks, landmarks_3d) -> bool:
        thumb_tip = landmarks[4]
        thumb_base = landmarks[2]
        index_base = landmarks[5]

        distance = np.linalg.norm(thumb_tip - thumb_base)
        palm_width = np.linalg.norm(landmarks[5] - landmarks[17])

        return distance > palm_width * 0.4

    def _classify_gesture(self, finger_states: Dict[str, bool], hand_data: HandData) -> GestureType:
        extended_count = sum(finger_states.values())

        landmarks = hand_data.landmarks_2d

        if extended_count == 5:
            return GestureType.OPEN_PALM

        elif extended_count == 0:
            return GestureType.FIST

        elif (finger_states['index'] and finger_states['middle'] and
              not finger_states['ring'] and not finger_states['pinky'] and
              not finger_states['thumb']):
            return GestureType.PEACE

        elif (finger_states['index'] and not finger_states['middle'] and
              not finger_states['ring'] and not finger_states['pinky']):
            if self._is_pointing_up(landmarks):
                return GestureType.POINTING_UP

        elif (finger_states['thumb'] and not finger_states['index'] and
              not finger_states['middle'] and not finger_states['ring'] and
              not finger_states['pinky']):
            return GestureType.THUMBS_UP

        elif (not finger_states['thumb'] and not finger_states['index'] and
              not finger_states['middle'] and not finger_states['ring'] and
              finger_states['pinky']):
            return GestureType.THUMBS_DOWN

        elif self._is_ok_sign(finger_states, landmarks):
            return GestureType.OK_SIGN

        elif self._is_pinch(finger_states, landmarks):
            return GestureType.PINCH

        elif self._is_two_finger_tap(finger_states):
            return GestureType.TWO_FINGER_TAP

        elif self._is_three_finger_tap(finger_states):
            return GestureType.THREE_FINGER_TAP

        elif self._is_index_click(finger_states):
            return GestureType.INDEX_CLICK

        swipe = self._detect_swipe(hand_data.hand_id)
        if swipe:
            return swipe

        if extended_count == 1:
            return GestureType.ONE_FINGER

        if finger_states['index'] and finger_states['middle']:
            return GestureType.TWO_FINGER_SCROLL

        return GestureType.UNKNOWN

    def _is_pointing_up(self, landmarks) -> bool:
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        wrist = landmarks[0]

        vertical = index_tip[1] < index_mcp[1] < wrist[1]

        return vertical

    def _is_ok_sign(self, finger_states: Dict[str, bool], landmarks) -> bool:
        if not (finger_states['index'] and finger_states['middle'] and
                finger_states['thumb']):
            return False

        index_tip = landmarks[8]
        thumb_tip = landmarks[4]

        distance = np.linalg.norm(index_tip - thumb_tip)
        return distance < 0.05

    def _is_pinch(self, finger_states: Dict[str, bool], landmarks) -> bool:
        if not finger_states['thumb'] or not finger_states['index']:
            return False

        index_tip = landmarks[8]
        thumb_tip = landmarks[4]

        distance = np.linalg.norm(index_tip - thumb_tip)
        return distance < 0.07

    def _is_two_finger_tap(self, finger_states: Dict[str, bool]) -> bool:
        return (finger_states['index'] and finger_states['middle'] and
                not finger_states['ring'] and not finger_states['pinky'])

    def _is_three_finger_tap(self, finger_states: Dict[str, bool]) -> bool:
        return (finger_states['index'] and finger_states['middle'] and
                finger_states['ring'] and not finger_states['pinky'])

    def _is_index_click(self, finger_states: Dict[str, bool]) -> bool:
        """Index folded, other fingers extended = wink/tap click."""
        return (not finger_states['index'] and
                finger_states['middle'] and
                finger_states['ring'] and
                finger_states['pinky'])

    def _detect_swipe(self, hand_id: int) -> Optional[GestureType]:
        if hand_id not in self._position_history:
            return None

        history = self._position_history[hand_id]
        if len(history) < 5:
            return None

        start_pos = np.array(history[0])
        end_pos = np.array(history[-1])
        displacement = end_pos - start_pos

        distance = np.linalg.norm(displacement)
        if distance < self.swipe_threshold:
            return None

        time_factor = len(history) / self._position_history_max
        velocity = distance / (time_factor + 0.1)

        if velocity < self.swipe_velocity_threshold:
            return None

        if abs(displacement[0]) > abs(displacement[1]):
            if displacement[0] > 0:
                return GestureType.SWIPE_RIGHT
            else:
                return GestureType.SWIPE_LEFT
        else:
            if displacement[1] > 0:
                return GestureType.SWIPE_DOWN
            else:
                return GestureType.SWIPE_UP

        return None

    def _update_position_history(self, hand_id: int, position: Tuple[int, int]):
        if hand_id not in self._position_history:
            self._position_history[hand_id] = []

        self._position_history[hand_id].append(position)

        if len(self._position_history[hand_id]) > self._position_history_max:
            self._position_history[hand_id].pop(0)

    def _calculate_confidence(self, finger_states: Dict[str, bool], gesture: GestureType) -> float:
        if gesture == GestureType.UNKNOWN:
            return 0.0

        base_confidence = 0.7

        extended_count = sum(finger_states.values())

        if gesture == GestureType.PEACE and extended_count == 2:
            return base_confidence + 0.2
        elif gesture == GestureType.FIST and extended_count == 0:
            return base_confidence + 0.2
        elif gesture == GestureType.OPEN_PALM and extended_count == 5:
            return base_confidence + 0.2

        return base_confidence

    def get_gesture_action(self, gesture: GestureType) -> str:
        from src.core.config import GESTURES
        return GESTURES.get(gesture.value, "unknown")

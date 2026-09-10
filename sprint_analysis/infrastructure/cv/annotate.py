"""Frame annotation utilities."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from sprint_analysis.domain.constants import CONNECTIONS, GROUP_COLORS, LANDMARKS
from sprint_analysis.domain.models import PoseLandmarks


class FrameAnnotator:
    """Draws keypoints, skeletons, and text overlays on frames."""

    def __init__(self, visibility_threshold: float = 0.5):
        self.visibility_threshold = visibility_threshold
        self.skeleton_color = (0, 255, 0)
        self.outline_color = (255, 255, 255)
        self.default_point_color = (0, 255, 0)
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_keypoints(
        self, frame: np.ndarray, landmarks: PoseLandmarks, colored: bool = True
    ) -> None:
        """Draw circles at each visible landmark position."""
        height, width = frame.shape[:2]

        for idx in range(33):
            lm = landmarks.landmarks.get(idx)
            if lm is None or lm.visibility < self.visibility_threshold:
                continue

            x, y = int(lm.x * width), int(lm.y * height)
            color = self._group_color(idx) if colored else self.default_point_color
            cv2.circle(frame, (x, y), 6, color, -1)
            cv2.circle(frame, (x, y), 8, self.outline_color, 1)

    def draw_skeleton(self, frame: np.ndarray, landmarks: PoseLandmarks) -> None:
        """Draw skeleton connections between visible landmarks."""
        height, width = frame.shape[:2]

        for idx_a, idx_b in CONNECTIONS:
            lm_a = landmarks.landmarks.get(idx_a)
            lm_b = landmarks.landmarks.get(idx_b)

            if (lm_a is None or lm_a.visibility < self.visibility_threshold or
                    lm_b is None or lm_b.visibility < self.visibility_threshold):
                continue

            pt_a = (int(lm_a.x * width), int(lm_a.y * height))
            pt_b = (int(lm_b.x * width), int(lm_b.y * height))
            cv2.line(frame, pt_a, pt_b, self.skeleton_color, 2)

    def draw_text(
        self,
        frame: np.ndarray,
        lines: List[Tuple[str, Tuple[int, int, int]]],
        x: int = 10,
        y: int = 25,
        step: int = 20,
        scale: float = 0.5,
        thickness: int = 1,
    ) -> int:
        """Draw text lines on frame. Returns final y position."""
        cursor = y
        for text, color in lines:
            cv2.putText(frame, text, (x, cursor), self.font, scale, color, thickness)
            cursor += step
        return cursor

    def _group_color(self, idx: int) -> Tuple[int, int, int]:
        """Get color for landmark group."""
        for group, indices in {
            "face": list(range(11)),
            "torso": list(range(11, 25)),
            "left_leg": [23, 25, 27, 29, 31],
            "right_leg": [24, 26, 28, 30, 32],
        }.items():
            if idx in indices:
                return GROUP_COLORS.get(group, self.default_point_color)
        return self.default_point_color

"""Pose detection implementation using MediaPipe."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

try:
    import mediapipe as mp

    MP_AVAILABLE = True
except ImportError:
    mp = None
    MP_AVAILABLE = False

from drone_analysis.domain.interfaces import PoseDetectorInterface
from drone_analysis.domain.models import Landmark3D, PoseLandmarks


class PoseDetector(PoseDetectorInterface):
    """MediaPipe Pose detector implementation."""

    def __init__(
        self,
        model_complexity: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ):
        if not MP_AVAILABLE:
            raise ImportError("mediapipe not installed: pip install mediapipe")

        self._pose_api = mp.solutions.pose
        self._drawing = mp.solutions.drawing_utils
        self._styles = mp.solutions.drawing_styles
        self._pose = self._pose_api.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, image: np.ndarray) -> Optional[PoseLandmarks]:
        """Detect pose landmarks in an RGB image."""
        results = self._pose.process(image)
        if not results.pose_landmarks:
            return None
        return self._to_domain(results.pose_landmarks.landmark)

    def detect_from_bgr(self, image: np.ndarray) -> Optional[PoseLandmarks]:
        """Detect pose landmarks in a BGR image."""
        import cv2
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return self.detect(rgb)

    def detect_in_roi(
        self,
        image_bgr: np.ndarray,
        bbox: Tuple[int, int, int, int],
    ) -> Optional[PoseLandmarks]:
        """Detect pose inside a bounding box and map landmarks to the original frame.

        Args:
            image_bgr: full original BGR frame.
            bbox: region of interest (x1, y1, x2, y2) in pixel coordinates.

        Returns:
            PoseLandmarks with coordinates normalized to the original frame.
        """
        import cv2

        x1, y1, x2, y2 = bbox
        h, w = image_bgr.shape[:2]
        if x1 < 0 or y1 < 0 or x2 > w or y2 > h or x2 <= x1 or y2 <= y1:
            return None

        crop = image_bgr[y1:y2, x1:x2]
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        crop_h, crop_w = crop.shape[:2]

        crop_landmarks = self.detect(rgb)
        if crop_landmarks is None:
            return None

        scale_x = crop_w / w
        scale_y = crop_h / h
        offset_x = x1 / w
        offset_y = y1 / h

        adjusted: Dict[int, Landmark3D] = {}
        for idx, lm in crop_landmarks.landmarks.items():
            adjusted[idx] = Landmark3D(
                x=lm.x * scale_x + offset_x,
                y=lm.y * scale_y + offset_y,
                z=lm.z * scale_x,
                visibility=lm.visibility,
            )
        return PoseLandmarks(landmarks=adjusted)

    def get_landmarks_array(self, results, width: int, height: int) -> np.ndarray:
        """Get landmarks as pixel coordinates array (33, 4)."""
        return np.array(
            [[lm.x * width, lm.y * height, lm.z, lm.visibility]
             for lm in results.pose_landmarks.landmark]
        )

    def draw_landmarks(self, frame_bgr: np.ndarray, results) -> None:
        """Draw landmarks and connections on frame."""
        self._drawing.draw_landmarks(
            frame_bgr,
            results.pose_landmarks,
            self._pose_api.POSE_CONNECTIONS,
            landmark_drawing_spec=self._styles.get_default_pose_landmarks_style(),
        )

    def _to_domain(self, landmarks) -> PoseLandmarks:
        """Convert MediaPipe landmarks to domain model."""
        domain_landmarks = {}
        for i, lm in enumerate(landmarks):
            domain_landmarks[i] = Landmark3D(
                x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility
            )
        return PoseLandmarks(landmarks=domain_landmarks)

    def close(self) -> None:
        self._pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

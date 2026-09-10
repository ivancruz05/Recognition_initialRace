"""Pose detection implementation using MediaPipe."""

from __future__ import annotations

from typing import Optional

import numpy as np

try:
    import mediapipe as mp

    MP_AVAILABLE = True
except ImportError:
    mp = None
    MP_AVAILABLE = False

from sprint_analysis.domain.interfaces import PoseDetectorInterface
from sprint_analysis.domain.models import Landmark3D, PoseLandmarks


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

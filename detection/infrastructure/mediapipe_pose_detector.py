"""MediaPipe implementation that translates model IDs at the infra boundary."""

from __future__ import annotations

from typing import Any, Dict, Optional

from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName


# MediaPipe Pose landmark identifiers are kept out of domain and application.
_MEDIAPIPE_LANDMARK_NAMES = {
    11: PoseLandmarkName.LEFT_SHOULDER,
    12: PoseLandmarkName.RIGHT_SHOULDER,
    13: PoseLandmarkName.LEFT_ELBOW,
    14: PoseLandmarkName.RIGHT_ELBOW,
    15: PoseLandmarkName.LEFT_WRIST,
    16: PoseLandmarkName.RIGHT_WRIST,
    23: PoseLandmarkName.LEFT_HIP,
    24: PoseLandmarkName.RIGHT_HIP,
    25: PoseLandmarkName.LEFT_KNEE,
    26: PoseLandmarkName.RIGHT_KNEE,
    27: PoseLandmarkName.LEFT_ANKLE,
    28: PoseLandmarkName.RIGHT_ANKLE,
    31: PoseLandmarkName.LEFT_FOOT_INDEX,
    32: PoseLandmarkName.RIGHT_FOOT_INDEX,
}


class MediaPipePoseDetector:
    """Detect one pose from a BGR image and return anatomically named points."""

    def __init__(
        self,
        *,
        model_complexity: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        try:
            import mediapipe as mp
        except ImportError as error:
            raise ImportError("mediapipe is required for pose detection") from error

        self._pose_api = mp.solutions.pose
        self._pose = self._pose_api.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._closed = False

    def detect_from_bgr(
        self, image: object
    ) -> Optional[Dict[PoseLandmarkName, PoseLandmark2D]]:
        """Convert a BGR image to RGB and map detected MediaPipe points."""
        if self._closed:
            raise RuntimeError("pose detector has been closed")

        import cv2

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self._pose.process(rgb_image)
        if not results.pose_landmarks:
            return None

        landmarks = {}
        for index, landmark_name in _MEDIAPIPE_LANDMARK_NAMES.items():
            point = results.pose_landmarks.landmark[index]
            landmarks[landmark_name] = PoseLandmark2D(
                x=point.x,
                y=point.y,
                visibility=point.visibility,
            )
        return landmarks

    def close(self) -> None:
        """Release MediaPipe resources; safe to call more than once."""
        if not self._closed:
            self._pose.close()
            self._closed = True

    def __enter__(self) -> "MediaPipePoseDetector":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

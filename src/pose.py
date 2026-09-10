"""Detector de pose corporal con MediaPipe (33 landmarks)."""

import numpy as np

try:
    import mediapipe as mp

    MP_AVAILABLE = True
except ImportError:
    mp = None
    MP_AVAILABLE = False

from src.landmarks import LANDMARKS


class PoseDetector:
    """Envuelve MediaPipe Pose para detectar y extraer landmarks corporales."""

    def __init__(self, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        if not MP_AVAILABLE:
            raise ImportError("mediapipe no está instalado: pip install mediapipe")

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

    def detect(self, frame_rgb):
        """Detecta pose en un frame RGB. Devuelve results o None si no hay detección."""
        results = self._pose.process(frame_rgb)
        return results if results.pose_landmarks else None

    def get_landmarks_normalized(self, results):
        """Landmarks como array (33, 4): [x, y, z, visibility] normalizados."""
        return np.array(
            [[lm.x, lm.y, lm.z, lm.visibility] for lm in results.pose_landmarks.landmark]
        )

    def get_landmarks_pixels(self, results, width, height):
        """Landmarks como array (33, 4): [x_px, y_px, z, visibility]."""
        return np.array(
            [[lm.x * width, lm.y * height, lm.z, lm.visibility]
             for lm in results.pose_landmarks.landmark]
        )

    def get_key_landmarks(self, results, width, height):
        """Devuelve dict nombre -> (x_px, y_px, z, visibility) para landmarks clave."""
        pixels = self.get_landmarks_pixels(results, width, height)
        return {name: pixels[idx] for name, idx in LANDMARKS.items()}

    def draw_landmarks(self, frame_bgr, results):
        """Dibuja landmarks y conexiones de MediaPipe sobre el frame."""
        self._drawing.draw_landmarks(
            frame_bgr,
            results.pose_landmarks,
            self._pose_api.POSE_CONNECTIONS,
            landmark_drawing_spec=self._styles.get_default_pose_landmarks_style(),
        )

    def close(self):
        self._pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
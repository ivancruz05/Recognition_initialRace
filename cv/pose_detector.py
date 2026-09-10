import cv2
import numpy as np
from pathlib import Path

try:
    import mediapipe as mp

    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False


class PoseDetector:
    """Wrapper de MediaPipe Pose para detectar 33 landmarks corporales."""

    # Indices de landmarks clave para sprint
    LANDMARKS = {
        "nose": 0,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28,
        "left_heel": 29,
        "right_heel": 30,
        "left_foot_index": 31,
        "right_foot_index": 32,
    }

    def __init__(self, model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        if not MP_AVAILABLE:
            raise ImportError("mediapipe no esta instalado. pip install mediapipe")

        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, frame_rgb):
        """Detecta pose en un frame RGB.

        Args:
            frame_rgb: imagen numpy en formato RGB (H, W, 3).

        Returns:
            results de MediaPipe Pose, o None si no detecta nada.
        """
        results = self.pose.process(frame_rgb)
        if not results.pose_landmarks:
            return None
        return results

    def get_landmarks_normalized(self, results):
        """Extrae landmarks como array normalizado (0-1).

        Args:
            results: resultado de MediaPipe Pose.

        Returns:
            ndarray de shape (33, 4) con [x, y, z, visibility] normalizados.
        """
        landmarks = results.pose_landmarks.landmark
        data = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks])
        return data

    def get_landmarks_pixels(self, results, width, height):
        """Extrae landmarks en coordenadas de pixel.

        Args:
            results: resultado de MediaPipe Pose.
            width, height: dimensiones del frame.

        Returns:
            ndarray de shape (33, 4) con [x_px, y_px, z, visibility].
        """
        landmarks = results.pose_landmarks.landmark
        data = np.array([
            [lm.x * width, lm.y * height, lm.z, lm.visibility]
            for lm in landmarks
        ])
        return data

    def get_key_landmarks(self, results, width, height):
        """Solo retorna landmarks clave para sprint (caderas, rodillas, etc).

        Returns:
            dict con nombre -> (x_px, y_px, z, visibility).
        """
        pixels = self.get_landmarks_pixels(results, width, height)
        return {name: pixels[idx] for name, idx in self.LANDMARKS.items()}

    def draw_landmarks(self, frame_bgr, results):
        """Dibuja landmarks y conexiones en un frame BGR.

        Args:
            frame_bgr: imagen numpy en formato BGR (modificada in-place).
            results: resultado de MediaPipe Pose.
        """
        self.mp_drawing.draw_landmarks(
            frame_bgr,
            results.pose_landmarks,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style(),
        )

    def close(self):
        self.pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

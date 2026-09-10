import cv2
import numpy as np
from pathlib import Path


class VideoReader:
    """Lee videos con OpenCV y retorna frames individuales."""

    def __init__(self, source):
        """
        Args:
            source: ruta a archivo de video (str/Path) o índice de cámara (int).
        """
        if isinstance(source, (str, Path)):
            self.cap = cv2.VideoCapture(str(source))
        else:
            self.cap = cv2.VideoCapture(source)

        if not self.cap.isOpened():
            raise ValueError(f"No se pudo abrir la fuente de video: {source}")

    def is_opened(self):
        return self.cap.isOpened()

    def read_frame(self):
        """Lee el siguiente frame.

        Returns:
            tuple: (ret, frame) donde frame es un ndarray BGR o None.
        """
        ret, frame = self.cap.read()
        if not ret:
            return False, None
        return True, frame

    def get_fps(self):
        return self.cap.get(cv2.CAP_PROP_FPS)

    def get_width(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    def get_height(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def get_frame_count(self):
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_resolution(self):
        return self.get_width(), self.get_height()

    def get_info(self):
        w, h = self.get_resolution()
        return {
            "fps": self.get_fps(),
            "width": w,
            "height": h,
            "frame_count": self.get_frame_count(),
            "duration_sec": self.get_frame_count() / self.get_fps() if self.get_fps() > 0 else 0,
        }

    def reset(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def release(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()

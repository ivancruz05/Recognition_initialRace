"""Apertura y selección de cámaras (FaceTime / iPhone) y archivos de video."""

from pathlib import Path

import cv2

from src.config import LOW_RES_THRESHOLD, MAX_CAMERA_INDEX


def list_cameras(max_index: int = MAX_CAMERA_INDEX) -> list:
    """Devuelve [(indice, ancho, alto)] de las cámaras disponibles."""
    cameras = []
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append((i, width, height))
        cap.release()
    return cameras


def find_iphone_camera():
    """Busca la cámara del iPhone (índice > 0 con alta resolución)."""
    for index, width, _ in list_cameras():
        if index > 0 and width >= LOW_RES_THRESHOLD:
            return index
    return None


def open_camera(index=None):
    """Abre una cámara y devuelve (capture, indice_usado) o (None, None)."""
    if index is not None:
        cap = cv2.VideoCapture(index)
        return (cap, index) if cap.isOpened() else (None, None)

    for i, _, _ in list_cameras():
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            return cap, i
    return None, None


class VideoPlayer:
    """Lee un archivo de video cuadro a cuadro (context manager)."""

    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise ValueError(f"No se pudo abrir el video: {path}")

    def read(self):
        return self.cap.read()

    def info(self):
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frames / fps if fps > 0 else 0
        return {"fps": fps, "width": width, "height": height, "frame_count": frames, "duration_sec": duration}

    def release(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()
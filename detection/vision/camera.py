"""Camera management utilities."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import cv2

from drone_analysis.domain.models import VideoInfo


class CameraManager:
    """Camera discovery and management."""

    def __init__(self, max_index: int = 4, low_res_threshold: int = 1920):
        self.max_index = max_index
        self.low_res_threshold = low_res_threshold

    def list_cameras(self) -> List[Tuple[int, int, int]]:
        """List available cameras as (index, width, height)."""
        cameras = []
        for i in range(self.max_index + 1):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cameras.append((i, width, height))
            cap.release()
        return cameras

    def find_iphone_camera(self) -> Optional[int]:
        """Find iPhone camera (high resolution, index > 0)."""
        for index, width, _ in self.list_cameras():
            if index > 0 and width >= self.low_res_threshold:
                return index
        return None

    def open_camera(self, index: Optional[int] = None) -> Tuple[Optional[cv2.VideoCapture], Optional[int]]:
        """Open a camera and return (capture, index)."""
        if index is not None:
            cap = cv2.VideoCapture(index)
            return (cap, index) if cap.isOpened() else (None, None)

        for i, _, _ in self.list_cameras():
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                return cap, i
        return None, None


class VideoPlayer:
    """Video file reader with context manager support."""

    def __init__(self, path: str):
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {path}")

    def read(self) -> Tuple[bool, Optional[any]]:
        return self.cap.read()

    def get_info(self) -> VideoInfo:
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return VideoInfo(
            path="",
            width=width,
            height=height,
            frame_count=frames,
            fps=fps,
        )

    def release(self) -> None:
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()

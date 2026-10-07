"""Sequential OpenCV frame source for MP4 and MOV files."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Union

from detection.domain.entities import CapturedFrame, RecognitionSession


PathLike = Union[str, Path]


class OpenCVVideoFileFrameSource:
    """Read MP4/MOV frames sequentially with timestamps derived from FPS."""

    SUPPORTED_EXTENSIONS = frozenset((".mp4", ".mov"))

    def __init__(self, path: PathLike, *, fallback_fps: float = 30.0) -> None:
        self.path = Path(path)
        if self.path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError("video path must have an .mp4 or .mov extension")
        if (
            isinstance(fallback_fps, bool)
            or not isinstance(fallback_fps, (int, float))
            or not math.isfinite(fallback_fps)
            or fallback_fps <= 0
        ):
            raise ValueError("fallback_fps must be a finite, positive number")

        self.fallback_fps = float(fallback_fps)
        self._capture: Any = None
        self._fps: Optional[float] = None
        self._frame_index = 0
        self._started = False

    def start(self, session: RecognitionSession) -> None:
        """Open the video, rejecting missing or unreadable files."""
        if self._started:
            raise RuntimeError("video source has already been started")
        if not self.path.is_file():
            raise ValueError("video file does not exist: {}".format(self.path))

        import cv2

        capture = cv2.VideoCapture(str(self.path))
        self._capture = capture
        try:
            if not capture.isOpened():
                raise ValueError("could not open video file: {}".format(self.path))

            fps = capture.get(cv2.CAP_PROP_FPS)
            if isinstance(fps, bool) or not isinstance(fps, (int, float)):
                fps = self.fallback_fps
            if not math.isfinite(fps) or fps <= 0:
                fps = self.fallback_fps
            self._fps = float(fps)
            self._frame_index = 0
            self._started = True
        except Exception:
            self.stop()
            raise

    def read_next(self) -> Optional[CapturedFrame]:
        """Return the next BGR frame, or release resources at end/error."""
        if not self._started:
            raise RuntimeError("video source has not been started")

        try:
            ok, image = self._capture.read()
            if not ok or image is None:
                self.stop()
                return None

            frame_index = self._frame_index
            frame = CapturedFrame(
                frame_index=frame_index,
                timestamp_seconds=frame_index / self._fps,
                payload=image,
            )
            self._frame_index += 1
            return frame
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        """Release the file capture; safe after EOF and repeated calls."""
        capture, self._capture = self._capture, None
        self._started = False
        if capture is not None:
            capture.release()

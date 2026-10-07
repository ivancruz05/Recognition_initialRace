"""OpenCV adapter for exclusive, unannotated live-capture MP4 output."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Union


PathLike = Union[str, Path]


class OpenCVRawVideoWriter:
    """Write original BGR frames to a new MP4 destination, never an overlay."""

    def __init__(
        self,
        path: PathLike,
        *,
        codec: str = "mp4v",
        cv2_module: Any = None,
        writer_factory: Any = None,
        verification_capture_factory: Any = None,
    ) -> None:
        self.path = Path(path)
        if self.path.suffix.lower() != ".mp4":
            raise ValueError("raw video output path must have an .mp4 extension")
        if not isinstance(codec, str) or len(codec) != 4:
            raise ValueError("codec must contain exactly four characters")
        self.codec = codec
        self._cv2 = cv2_module
        self._writer_factory = writer_factory
        self._verification_capture_factory = verification_capture_factory
        self._writer: Any = None
        self._reservation_created = False
        self._writer_opened = False
        self._frames_written = 0

    @property
    def is_started(self) -> bool:
        return self._writer is not None

    @property
    def frames_written(self) -> int:
        """Number of frames accepted by the encoder without raising."""
        return self._frames_written

    def start(self, *, fps: float, frame_size: tuple[int, int]) -> None:
        """Reserve a new target exclusively, then open its MP4 encoder."""
        if self._writer is not None:
            raise RuntimeError("raw video writer is already started")
        if (
            isinstance(fps, bool)
            or not isinstance(fps, (int, float))
            or not math.isfinite(fps)
            or fps <= 0
        ):
            raise ValueError("fps must be finite and positive")
        if (
            len(frame_size) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in frame_size)
        ):
            raise ValueError("frame_size must contain positive integer width and height")

        self._frames_written = 0
        reservation = self.path.open("xb")
        reservation.close()
        self._reservation_created = True
        try:
            cv2 = self._cv2
            if cv2 is None and self._writer_factory is None:
                import cv2 as cv2_module

                cv2 = cv2_module
                self._cv2 = cv2
            if self._writer_factory is not None:
                writer = self._writer_factory(
                    str(self.path), float(fps), frame_size
                )
            else:
                fourcc = cv2.VideoWriter_fourcc(*self.codec)
                writer = cv2.VideoWriter(str(self.path), fourcc, float(fps), frame_size)
            self._writer = writer
            is_opened = getattr(writer, "isOpened", None)
            if callable(is_opened) and not is_opened():
                raise RuntimeError("could not open raw video output: {}".format(self.path))
            self._writer_opened = True
        except BaseException:
            try:
                self.stop()
            except BaseException:
                pass
            raise

    def write(self, image: object) -> None:
        """Write one original, unmodified BGR image."""
        if self._writer is None:
            raise RuntimeError("raw video writer has not been started")
        self._writer.write(image)
        self._frames_written += 1

    def stop(self) -> None:
        """Release and decode-check a started recording, retaining partial files."""
        writer, self._writer = self._writer, None
        writer_opened, self._writer_opened = self._writer_opened, False
        try:
            if writer is not None:
                writer.release()
            if writer is not None and writer_opened:
                self._verify_output()
        except BaseException:
            if self._reservation_created and not writer_opened:
                self._remove_failed_reservation()
            raise
        finally:
            # A failed open leaves only our exclusive placeholder behind.
            if not writer_opened and self._reservation_created:
                self._remove_failed_reservation()
            self._reservation_created = False

    def _verify_output(self) -> None:
        """Decode the finished MP4 and compare its frames with accepted writes."""
        try:
            capture_factory = self._verification_capture_factory
            if capture_factory is None:
                cv2 = self._cv2
                if cv2 is None:
                    import cv2 as cv2_module

                    cv2 = cv2_module
                    self._cv2 = cv2
                capture_factory = cv2.VideoCapture
            capture = capture_factory(str(self.path))
        except Exception as exc:
            raise RuntimeError(
                "could not open raw video for verification: {}".format(self.path)
            ) from exc

        decoded_frames = 0
        try:
            is_opened = getattr(capture, "isOpened", None)
            if not callable(is_opened) or not is_opened():
                raise RuntimeError(
                    "could not open raw video for verification: {}".format(self.path)
                )
            while True:
                success, _ = capture.read()
                if not success:
                    break
                decoded_frames += 1
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(
                "could not decode raw video for verification: {}".format(self.path)
            ) from exc
        finally:
            try:
                capture.release()
            except Exception as exc:
                raise RuntimeError(
                    "could not release raw video decoder: {}".format(self.path)
                ) from exc

        if decoded_frames < 1:
            raise RuntimeError(
                "raw video verification decoded no frames: {}".format(self.path)
            )
        if decoded_frames != self._frames_written:
            raise RuntimeError(
                "raw video verification frame count mismatch for {}: "
                "expected {}, decoded {}".format(
                    self.path, self._frames_written, decoded_frames
                )
            )

    def _remove_failed_reservation(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

"""OpenCV camera source with a pose-quality-gated manual capture preview."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional, Protocol, Union

from detection.domain.angle_calculation import calculate_biomechanical_angles
from detection.domain.entities import (
    BiomechanicalFrameResult,
    CapturedFrame,
    RecognitionSession,
)
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName
from detection.infrastructure.frame_payload import AnalyzedFramePayload
from detection.infrastructure.raw_video_writer import OpenCVRawVideoWriter


class PreviewPoseDetector(Protocol):
    def detect_from_bgr(
        self, image: object
    ) -> Optional[Mapping[PoseLandmarkName, PoseLandmark2D]]:
        ...


class RawVideoWriter(Protocol):
    def start(self, *, fps: float, frame_size: tuple[int, int]) -> None:
        ...

    def write(self, image: object) -> None:
        ...

    def stop(self) -> None:
        ...


PathLike = Union[str, Path]


class OpenCVCameraFrameSource:
    """Capture BGR frames after five consecutive pose-ready preview frames.

    Preview landmarks are cached in each returned frame payload. The analyzer
    can therefore consume the same observation without running MediaPipe again.
    If ``raw_video_path`` is configured, the original BGR frame at the ``t``
    keypress is the first video frame; the rendered preview is never recorded.
    """

    SKELETON_CONNECTIONS = (
        (PoseLandmarkName.LEFT_SHOULDER, PoseLandmarkName.RIGHT_SHOULDER),
        (PoseLandmarkName.LEFT_SHOULDER, PoseLandmarkName.LEFT_HIP),
        (PoseLandmarkName.RIGHT_SHOULDER, PoseLandmarkName.RIGHT_HIP),
        (PoseLandmarkName.LEFT_SHOULDER, PoseLandmarkName.LEFT_ELBOW),
        (PoseLandmarkName.LEFT_ELBOW, PoseLandmarkName.LEFT_WRIST),
        (PoseLandmarkName.RIGHT_SHOULDER, PoseLandmarkName.RIGHT_ELBOW),
        (PoseLandmarkName.RIGHT_ELBOW, PoseLandmarkName.RIGHT_WRIST),
        (PoseLandmarkName.LEFT_HIP, PoseLandmarkName.RIGHT_HIP),
        (PoseLandmarkName.LEFT_HIP, PoseLandmarkName.LEFT_KNEE),
        (PoseLandmarkName.LEFT_KNEE, PoseLandmarkName.LEFT_ANKLE),
        (PoseLandmarkName.LEFT_ANKLE, PoseLandmarkName.LEFT_FOOT_INDEX),
        (PoseLandmarkName.RIGHT_HIP, PoseLandmarkName.RIGHT_KNEE),
        (PoseLandmarkName.RIGHT_KNEE, PoseLandmarkName.RIGHT_ANKLE),
        (PoseLandmarkName.RIGHT_ANKLE, PoseLandmarkName.RIGHT_FOOT_INDEX),
    )
    PREVIEW_FPS_WINDOW = 30

    def __init__(
        self,
        camera_index: int,
        *,
        backend: Optional[int] = None,
        window_name: str = "Recognition camera preview",
        pose_detector: Optional[PreviewPoseDetector] = None,
        pose_detector_factory: Any = None,
        readiness_frames: int = 5,
        visibility_threshold: float = 0.5,
        raw_video_path: Optional[PathLike] = None,
        raw_video_writer: Optional[RawVideoWriter] = None,
        fallback_fps: float = 30.0,
    ) -> None:
        if isinstance(camera_index, bool) or not isinstance(camera_index, int):
            raise ValueError("camera_index must be an integer")
        if camera_index < 0:
            raise ValueError("camera_index must be non-negative")
        if backend is not None and (
            isinstance(backend, bool) or not isinstance(backend, int)
        ):
            raise ValueError("backend must be an integer or None")
        if not isinstance(window_name, str) or not window_name.strip():
            raise ValueError("window_name must be a non-empty string")
        if isinstance(readiness_frames, bool) or not isinstance(readiness_frames, int):
            raise ValueError("readiness_frames must be a positive integer")
        if readiness_frames < 1:
            raise ValueError("readiness_frames must be a positive integer")
        if (
            isinstance(visibility_threshold, bool)
            or not isinstance(visibility_threshold, (int, float))
            or not math.isfinite(visibility_threshold)
            or visibility_threshold < 0
            or visibility_threshold > 1
        ):
            raise ValueError("visibility_threshold must be between 0 and 1")
        if (
            isinstance(fallback_fps, bool)
            or not isinstance(fallback_fps, (int, float))
            or not math.isfinite(fallback_fps)
            or fallback_fps <= 0
        ):
            raise ValueError("fallback_fps must be finite and positive")
        if raw_video_path is not None and Path(raw_video_path).suffix.lower() != ".mp4":
            raise ValueError("raw video path must have an .mp4 extension")

        self.camera_index = camera_index
        self.backend = backend
        self.window_name = window_name
        self.readiness_frames = readiness_frames
        self.visibility_threshold = float(visibility_threshold)
        self.raw_video_path = Path(raw_video_path) if raw_video_path is not None else None
        self._pose_detector = pose_detector
        self._pose_detector_factory = pose_detector_factory
        self._owns_pose_detector = False
        self._raw_video_writer = raw_video_writer
        if self._raw_video_writer is None and self.raw_video_path is not None:
            self._raw_video_writer = OpenCVRawVideoWriter(self.raw_video_path)
        self._fallback_fps = float(fallback_fps)

        self._capture: Any = None
        self._cv2: Any = None
        self._window_created = False
        self._started = False
        self._collecting = False
        self._frame_index = 0
        self._ready_streak = 0
        self._capture_started_at: Optional[float] = None
        self._preview_arrivals: deque[float] = deque(maxlen=self.PREVIEW_FPS_WINDOW)
        self._session: Optional[RecognitionSession] = None
        self._fps = self._fallback_fps
        self._raw_video_frames_written = 0

    @property
    def raw_video_frames_written(self) -> int:
        """Number of raw camera frames successfully passed to the video writer."""
        return self._raw_video_frames_written

    def start(self, session: RecognitionSession) -> None:
        """Open the configured camera and initialize pose-gated preview."""
        if self._started:
            raise RuntimeError("camera source has already been started")
        if self.raw_video_path is not None and self.raw_video_path.exists():
            raise FileExistsError("raw video output already exists: {}".format(self.raw_video_path))

        import cv2

        self._cv2 = cv2
        try:
            self._collecting = False
            self._frame_index = 0
            self._ready_streak = 0
            self._capture_started_at = None
            self._preview_arrivals.clear()
            self._raw_video_frames_written = 0
            self._session = session
            if self.backend is None:
                capture = cv2.VideoCapture(self.camera_index)
            else:
                capture = cv2.VideoCapture(self.camera_index, self.backend)
            self._capture = capture
            if not capture.isOpened():
                raise RuntimeError(
                    "could not open camera index {}".format(self.camera_index)
                )
            self._fps = self._read_camera_fps(capture, cv2)
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            self._window_created = True
            if self._pose_detector is None:
                if self._pose_detector_factory is None:
                    from detection.infrastructure.mediapipe_pose_detector import (
                        MediaPipePoseDetector,
                    )

                    self._pose_detector = MediaPipePoseDetector()
                else:
                    self._pose_detector = self._pose_detector_factory()
                self._owns_pose_detector = True
            self._started = True
        except Exception:
            try:
                self.stop()
            except Exception:
                pass
            raise

    def read_next(self) -> Optional[CapturedFrame]:
        """Preview until ready; then return one cached-pose frame per call."""
        if not self._started:
            raise RuntimeError("camera source has not been started")

        try:
            while True:
                ok, image = self._capture.read()
                if not ok or image is None:
                    self.stop()
                    return None
                frame_read_at = time.monotonic()
                self._preview_arrivals.append(frame_read_at)

                height, width = self._image_dimensions(image)
                landmarks = self._pose_detector.detect_from_bgr(image)
                if landmarks is not None and not isinstance(landmarks, Mapping):
                    raise TypeError("pose detector must return a landmark mapping or None")
                angles = calculate_biomechanical_angles(
                    landmarks or {},
                    image_width=width,
                    image_height=height,
                    visibility_threshold=self.visibility_threshold,
                )
                preview_result = BiomechanicalFrameResult(
                    session=self._session,
                    frame_index=self._frame_index,
                    timestamp_seconds=0.0,
                    angles=angles,
                    pose_detected=landmarks is not None,
                    landmarks=landmarks or {},
                )
                if preview_result.pose_ready:
                    self._ready_streak += 1
                else:
                    self._ready_streak = 0

                annotated = self._render_preview(
                    image,
                    landmarks or {},
                    height,
                    width,
                    recording=self._collecting,
                )
                self._cv2.imshow(self.window_name, annotated)
                key = self._cv2.waitKey(1) & 0xFF

                if key == ord("q") or key == ord("s"):
                    self.stop()
                    return None
                if key == ord("t") and not self._collecting:
                    if self._ready_streak < self.readiness_frames:
                        continue
                    self._collecting = True
                    # Anchor both CSV elapsed time and frame 0 to this frame's
                    # arrival, not to preview rendering or key polling.
                    self._capture_started_at = frame_read_at
                    if self._raw_video_writer is not None:
                        self._raw_video_writer.start(
                            fps=self._estimate_preview_fps() or self._fps,
                            frame_size=(width, height),
                        )
                    # Replace the READY preview immediately after accepting t.
                    self._cv2.imshow(
                        self.window_name,
                        self._render_preview(
                            image, landmarks or {}, height, width, recording=True
                        ),
                    )

                if self._collecting:
                    if self._raw_video_writer is not None:
                        self._raw_video_writer.write(image)
                        self._raw_video_frames_written += 1
                    timestamp = max(
                        0.0, frame_read_at - self._capture_started_at
                    )
                    frame = CapturedFrame(
                        frame_index=self._frame_index,
                        timestamp_seconds=timestamp,
                        payload=AnalyzedFramePayload(image, landmarks),
                    )
                    self._frame_index += 1
                    return frame
        except Exception:
            try:
                self.stop()
            except Exception:
                pass
            raise

    def stop(self) -> None:
        """Release every owned camera, encoder, detector, and preview resource."""
        errors = []
        capture, self._capture = self._capture, None
        if capture is not None:
            try:
                capture.release()
            except BaseException as error:
                errors.append(error)

        writer = self._raw_video_writer
        if writer is not None:
            try:
                writer.stop()
            except BaseException as error:
                errors.append(error)

        detector = self._pose_detector if self._owns_pose_detector else None
        self._pose_detector = None if self._owns_pose_detector else self._pose_detector
        self._owns_pose_detector = False
        if detector is not None:
            try:
                detector.close()
            except BaseException as error:
                errors.append(error)

        if self._window_created and self._cv2 is not None:
            self._window_created = False
            try:
                self._cv2.destroyWindow(self.window_name)
            except Exception:
                # The window can already have been closed by the operating system.
                pass

        self._started = False
        self._collecting = False
        self._ready_streak = 0
        self._capture_started_at = None
        self._session = None
        if errors:
            raise errors[0]

    def _read_camera_fps(self, capture: Any, cv2: Any) -> float:
        try:
            value = capture.get(cv2.CAP_PROP_FPS)
        except Exception:
            return self._fallback_fps
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            return self._fallback_fps
        try:
            fps = float(value)
        except (OverflowError, TypeError, ValueError):
            return self._fallback_fps
        if not math.isfinite(fps) or fps <= 0:
            return self._fallback_fps
        return fps

    def _estimate_preview_fps(self) -> Optional[float]:
        """Estimate the sampled-frame rate from recent successful reads."""
        if len(self._preview_arrivals) < 2:
            return None
        elapsed = self._preview_arrivals[-1] - self._preview_arrivals[0]
        if not math.isfinite(elapsed) or elapsed <= 0:
            return None
        fps = (len(self._preview_arrivals) - 1) / elapsed
        if not math.isfinite(fps) or fps <= 0:
            return None
        return fps

    @staticmethod
    def _image_dimensions(image: object) -> tuple[int, int]:
        shape = getattr(image, "shape", None)
        if shape is None or len(shape) < 2:
            raise ValueError("camera frame must be an image with height and width")
        height, width = int(shape[0]), int(shape[1])
        if height <= 0 or width <= 0:
            raise ValueError("camera frame must have positive height and width")
        return height, width

    def _render_preview(
        self,
        image: object,
        landmarks: Mapping[PoseLandmarkName, PoseLandmark2D],
        height: int,
        width: int,
        *,
        recording: bool,
    ) -> object:
        canvas = image.copy()
        cv2 = self._cv2
        for first_name, second_name in self.SKELETON_CONNECTIONS:
            first = landmarks.get(first_name)
            second = landmarks.get(second_name)
            if (
                first is None
                or second is None
                or first.visibility < self.visibility_threshold
                or second.visibility < self.visibility_threshold
            ):
                continue
            cv2.line(
                canvas,
                (int(first.x * width), int(first.y * height)),
                (int(second.x * width), int(second.y * height)),
                (60, 220, 80),
                2,
            )
        for point in landmarks.values():
            if point.visibility >= self.visibility_threshold:
                cv2.circle(
                    canvas,
                    (int(point.x * width), int(point.y * height)),
                    4,
                    (0, 220, 255),
                    -1,
                )

        if recording:
            status = "RECORDING | s: finish | q: stop"
            color = (0, 0, 255)
        elif self._ready_streak >= self.readiness_frames:
            status = (
                "READY | lower-limb angles available; lateral view NOT verified | t: start"
            )
            color = (60, 220, 80)
        else:
            status = "POSE NOT READY ({}/{}) | need {} consecutive frames".format(
                self._ready_streak,
                self.readiness_frames,
                self.readiness_frames,
            )
            color = (0, 165, 255)
        cv2.putText(
            canvas,
            status,
            (12, 28),
            getattr(cv2, "FONT_HERSHEY_SIMPLEX", 0),
            0.55,
            color,
            2,
        )
        return canvas

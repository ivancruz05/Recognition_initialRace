"""Adapt detected anatomical landmarks into biomechanical frame results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Optional, Protocol

from detection.domain.angle_calculation import calculate_biomechanical_angles
from detection.domain.entities import (
    BiomechanicalFrameResult,
    CapturedFrame,
    RecognitionSession,
)
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName
from detection.infrastructure.frame_payload import AnalyzedFramePayload


class PoseDetectorPort(Protocol):
    """Detect a pose in a BGR image and return anatomical domain landmarks."""

    def detect_from_bgr(
        self, image: object
    ) -> Optional[Mapping[PoseLandmarkName, PoseLandmark2D]]:
        ...


class MediaPipeBiomechanicalAnalyzer:
    """Pass detector-provided anatomical landmarks to the domain angle rules."""

    def __init__(
        self,
        pose_detector: PoseDetectorPort,
        *,
        visibility_threshold: float = 0.5,
    ) -> None:
        self._pose_detector = pose_detector
        self._visibility_threshold = visibility_threshold

    def analyze(
        self, session: RecognitionSession, frame: CapturedFrame
    ) -> BiomechanicalFrameResult:
        payload = frame.payload
        if isinstance(payload, AnalyzedFramePayload):
            image = payload.image
            landmarks = payload.landmarks
            pose_detected = payload.pose_detected
        else:
            image = payload
            landmarks = None
            pose_detected = False

        shape = getattr(image, "shape", None)
        if shape is None or len(shape) < 2:
            raise ValueError("frame payload must be an image with height and width")
        image_height, image_width = int(shape[0]), int(shape[1])

        if not isinstance(payload, AnalyzedFramePayload):
            landmarks = self._pose_detector.detect_from_bgr(image)
            pose_detected = landmarks is not None
        if landmarks is None:
            landmarks = {}
        elif not isinstance(landmarks, Mapping):
            raise TypeError("pose detector must return a landmark mapping or None")

        angles = calculate_biomechanical_angles(
            landmarks,
            image_width=image_width,
            image_height=image_height,
            visibility_threshold=self._visibility_threshold,
        )
        return BiomechanicalFrameResult(
            session=session,
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            angles=angles,
            pose_detected=pose_detected,
            landmarks=landmarks,
        )

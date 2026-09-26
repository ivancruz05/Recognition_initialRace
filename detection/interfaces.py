"""Abstract contracts for the swappable adapters in `detection.vision`.

Implemented today:
    PoseDetectorInterface     -> vision.pose.PoseDetector
    BodyMeasurementInterface  -> metrics.measurements.BodyMeasurementAnalyzer

Structural contract (satisfied by vision.calibration.ArUcoCalibration without
inheriting, so metrics/ never has to import vision/):
    PixelToWorldTransform

Reserved, no implementation yet (RealSense `.r3d` depth ingest is the pending
consumer). Delete them if that work is abandoned:
    DepthProviderInterface
    VideoParserInterface
"""

from abc import ABC, abstractmethod
from typing import Optional, Protocol, Tuple, runtime_checkable

import numpy as np

from detection.entities import (
    DepthFrame,
    PoseLandmarks,
    VideoInfo,
)


class PoseDetectorInterface(ABC):
    """Interface for pose detection implementations."""

    @abstractmethod
    def detect(self, image: np.ndarray) -> Optional[PoseLandmarks]:
        """Detect pose landmarks in an RGB image."""
        ...

    @abstractmethod
    def detect_from_bgr(self, image: np.ndarray) -> Optional[PoseLandmarks]:
        """Detect pose landmarks in a BGR image."""
        ...

    @abstractmethod
    def detect_in_roi(
        self,
        image_bgr: np.ndarray,
        bbox: Tuple[int, int, int, int],
    ) -> Optional[PoseLandmarks]:
        """Detect pose inside a bounding box, mapping landmarks back to the full frame.

        Args:
            image_bgr: full original BGR frame.
            bbox: region of interest (x1, y1, x2, y2) in pixel coordinates.
        """
        ...


class DepthProviderInterface(ABC):
    """Interface for depth data providers."""

    @abstractmethod
    def get_frame(self, index: int) -> Optional[DepthFrame]:
        """Get depth frame at given index."""
        ...

    @abstractmethod
    def get_info(self) -> VideoInfo:
        """Get video metadata."""
        ...


class VideoParserInterface(ABC):
    """Interface for video file parsers."""

    @abstractmethod
    def parse(self, path: str) -> VideoInfo:
        """Parse video file and return metadata."""
        ...

    @abstractmethod
    def get_frame(self, index: int) -> Optional[DepthFrame]:
        """Get frame with RGB and optional depth data."""
        ...


class BodyMeasurementInterface(ABC):
    """Interface for body measurement implementations."""

    @abstractmethod
    def measure(
        self,
        landmarks: PoseLandmarks,
        depth_frame: Optional[DepthFrame] = None,
        known_height_cm: Optional[float] = None,
        image_shape: Optional[Tuple[int, int]] = None,
    ) -> "BodyMeasurements":
        """Measure body dimensions from landmarks and optional depth.

        Args:
            landmarks: 33 detected skeleton landmarks.
            depth_frame: Optional per-pixel depth aligned to the RGB frame.
            known_height_cm: Athlete height, used to scale when depth is absent.
            image_shape: (height, width) of the source frame, required with depth.
        """
        ...


@runtime_checkable
class PixelToWorldTransform(Protocol):
    """Anything that can map pixel coordinates to world units (meters).

    Satisfied structurally by `vision.calibration.ArUcoCalibration`, so pure
    math in `detection.metrics` can depend on the operation instead of the
    concrete calibrator.
    """

    def image_to_world(self, points_px: np.ndarray) -> np.ndarray:
        """Map an (N, 2) array of pixel coordinates to (N, 2) world meters."""
        ...

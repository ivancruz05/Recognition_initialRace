"""Domain interfaces - Abstract base classes."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

import numpy as np

from sprint_analysis.domain.models import (
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
    ) -> "BodyMeasurements":
        """Measure body dimensions from landmarks and optional depth."""
        ...

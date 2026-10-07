"""Framework-independent domain for live and file-based recognition."""

from detection.domain.entities import (
    BiomechanicalAngles,
    BiomechanicalFrameResult,
    CapturedFrame,
    RecognitionSession,
)
from detection.domain.exceptions import DomainInvariantError
from detection.domain.ports import BiomechanicalAnalyzer, FrameResultWriter, FrameSource
from detection.domain.angle_calculation import (
    calculate_angle_at,
    calculate_biomechanical_angles,
)
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName

__all__ = [
    "BiomechanicalAnalyzer",
    "BiomechanicalAngles",
    "BiomechanicalFrameResult",
    "PoseLandmark2D",
    "PoseLandmarkName",
    "CapturedFrame",
    "DomainInvariantError",
    "FrameResultWriter",
    "FrameSource",
    "RecognitionSession",
    "calculate_angle_at",
    "calculate_biomechanical_angles",
]

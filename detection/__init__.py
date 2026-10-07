"""Local single-athlete pose recognition with per-frame CSV results.

The package is organized into a pure domain, application session use case,
OpenCV/MediaPipe infrastructure adapters, and ``python -m detection`` CLI.
"""

from detection.application import (
    RecognitionSessionProcessor,
    SessionProcessingRequest,
    SessionProcessingResult,
    SessionProcessorState,
)
from detection.domain import (
    BiomechanicalAngles,
    BiomechanicalFrameResult,
    BiomechanicalAnalyzer,
    CapturedFrame,
    DomainInvariantError,
    FrameResultWriter,
    FrameSource,
    PoseLandmark2D,
    PoseLandmarkName,
    RecognitionSession,
    calculate_angle_at,
    calculate_biomechanical_angles,
)

__version__ = "1.0.0"

__all__ = [
    "BiomechanicalAngles",
    "BiomechanicalAnalyzer",
    "BiomechanicalFrameResult",
    "CapturedFrame",
    "DomainInvariantError",
    "FrameResultWriter",
    "FrameSource",
    "PoseLandmark2D",
    "PoseLandmarkName",
    "RecognitionSession",
    "RecognitionSessionProcessor",
    "SessionProcessingRequest",
    "SessionProcessingResult",
    "SessionProcessorState",
    "calculate_angle_at",
    "calculate_biomechanical_angles",
]


def __dir__():
    return sorted(set(globals()) | set(__all__))

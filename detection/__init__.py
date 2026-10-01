"""Detection module - everything that turns drone video into biomechanical metrics.

Layout:
    entities.py    core dataclasses (no I/O)
    constants.py   landmark tables and reference proportions
    interfaces.py  abstract contracts for swappable adapters
    metrics/       pure biomechanical math (no I/O)
    vision/        adapters that touch cv2 / mediapipe / ultralytics
    pipeline.py    end-to-end orchestration
    service.py     analysis + measurement orchestration
    pipelines.py   specialised pipelines (measurements, pose quality)
    cli.py         click commands
"""

from detection.entities import (
    AnalysisReport,
    BiomechanicalAngles,
    BodyMeasurements,
    ComparisonResult,
    DepthFrame,
    KinematicsResult,
    Landmark3D,
    PoseLandmarks,
    SprintMetrics,
    TrackingResult,
    VideoInfo,
)
from detection.constants import (
    BODY_PROPORTIONS,
    CONNECTIONS,
    LANDMARKS,
    OPTIMAL_ANGLES,
)
from detection.interfaces import (
    BodyMeasurementInterface,
    DepthProviderInterface,
    PoseDetectorInterface,
    VideoParserInterface,
)

__version__ = "1.0.0"

__all__ = [
    "AnalysisReport",
    "BiomechanicalAngles",
    "BODY_PROPORTIONS",
    "BodyMeasurementInterface",
    "BodyMeasurements",
    "CONNECTIONS",
    "ComparisonResult",
    "DepthFrame",
    "DepthProviderInterface",
    "KinematicsResult",
    "LANDMARKS",
    "Landmark3D",
    "OPTIMAL_ANGLES",
    "PoseDetectorInterface",
    "PoseLandmarks",
    "SprintMetrics",
    "TrackingResult",
    "VideoInfo",
    "VideoParserInterface",
]

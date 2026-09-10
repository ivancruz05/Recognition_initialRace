"""Domain models - Core data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class LandmarkIndex(Enum):
    """MediaPipe Pose landmark indices."""
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32


@dataclass(frozen=True)
class Landmark3D:
    """Single 3D landmark with coordinates and confidence."""
    x: float
    y: float
    z: float
    visibility: float

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "Landmark3D":
        return cls(x=float(arr[0]), y=float(arr[1]), z=float(arr[2]), visibility=float(arr[3]))

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z, self.visibility])


@dataclass
class PoseLandmarks:
    """Collection of 33 pose landmarks."""
    landmarks: Dict[int, Landmark3D] = field(default_factory=dict)

    def get(self, index: LandmarkIndex) -> Optional[Landmark3D]:
        return self.landmarks.get(index.value)

    def get_array(self, index: LandmarkIndex) -> Optional[np.ndarray]:
        lm = self.get(index)
        return lm.to_array() if lm else None

    @property
    def is_valid(self) -> bool:
        return len(self.landmarks) > 10


@dataclass
class BodyMeasurements:
    """Physical body measurements in centimeters."""
    height_cm: float
    leg_length_cm: float
    arm_length_cm: float
    torso_length_cm: float
    foot_length_cm: float
    shoulder_width_cm: float
    confidence: float = 1.0
    depth_valid_ratio: float = 0.0


@dataclass
class BiomechanicalAngles:
    """Angles calculated from pose landmarks."""
    left_knee: float = 0.0
    right_knee: float = 0.0
    left_hip: float = 0.0
    right_hip: float = 0.0
    left_ankle: float = 0.0
    right_ankle: float = 0.0
    trunk_angle: float = 0.0


@dataclass
class SprintMetrics:
    """Sprint performance metrics."""
    reaction_time_ms: float = 0.0
    velocity_ms: float = 0.0
    quality_score: float = 0.0
    angles: BiomechanicalAngles = field(default_factory=BiomechanicalAngles)


@dataclass
class ComparisonResult:
    """Result of comparing against optimal reference."""
    deviations: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    overall_score: float = 0.0


@dataclass
class VideoInfo:
    """Metadata about a video file."""
    path: str
    width: int = 0
    height: int = 0
    frame_count: int = 0
    fps: float = 0.0
    has_depth: bool = False


@dataclass
class DepthFrame:
    """A single depth frame with RGB and depth data."""
    rgb: Optional[np.ndarray] = None
    depth: Optional[np.ndarray] = None
    confidence: Optional[np.ndarray] = None
    frame_index: int = 0


@dataclass
class AnalysisReport:
    """Complete analysis report for an athlete."""
    athlete_name: str
    video_path: str
    measurements: BodyMeasurements
    metrics: SprintMetrics
    comparison: ComparisonResult
    recommendations: List[str] = field(default_factory=list)
    frames_analyzed: int = 0

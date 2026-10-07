"""Small, immutable value objects for a recognition session."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional

from detection.domain.exceptions import DomainInvariantError
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName


def _require_identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DomainInvariantError("{} must be a non-empty string".format(name))


@dataclass(frozen=True)
class RecognitionSession:
    """Identity for one manually controlled, single-athlete analysis session."""

    session_id: str
    athlete_id: str

    def __post_init__(self) -> None:
        _require_identifier(self.session_id, "session_id")
        _require_identifier(self.athlete_id, "athlete_id")


@dataclass(frozen=True)
class CapturedFrame:
    """A source frame and its source-assigned position in the session.

    ``payload`` is intentionally opaque: a live camera adapter or a future
    video-file adapter can supply its own frame representation without making
    the domain depend on OpenCV or a codec.
    """

    frame_index: int
    timestamp_seconds: float
    payload: Any = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.frame_index, bool) or not isinstance(self.frame_index, int):
            raise DomainInvariantError("frame_index must be an integer")
        if self.frame_index < 0:
            raise DomainInvariantError("frame_index must be non-negative")
        if (
            isinstance(self.timestamp_seconds, bool)
            or not isinstance(self.timestamp_seconds, (int, float))
            or not math.isfinite(self.timestamp_seconds)
            or self.timestamp_seconds < 0
        ):
            raise DomainInvariantError(
                "timestamp_seconds must be a finite, non-negative number"
            )
        if self.payload is None:
            raise DomainInvariantError("payload must contain a source frame")


@dataclass(frozen=True)
class BiomechanicalAngles:
    """Per-frame joint angles in degrees; ``None`` means unavailable/invalid.

    Values are kept as angles only. No speed, distance, or world-space
    measurement is inferred without camera calibration.
    """

    left_knee_deg: Optional[float] = None
    right_knee_deg: Optional[float] = None
    left_hip_deg: Optional[float] = None
    right_hip_deg: Optional[float] = None
    left_ankle_deg: Optional[float] = None
    right_ankle_deg: Optional[float] = None
    trunk_angle_deg: Optional[float] = None

    def __post_init__(self) -> None:
        for name, value in self.as_dict().items():
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
                or value > 180
            ):
                raise DomainInvariantError(
                    "{} must be None or a finite angle between 0 and 180 degrees".format(
                        name
                    )
                )

    @property
    def validity(self) -> Mapping[str, bool]:
        """Validity for each angle, derived from whether its value is present."""
        return MappingProxyType(
            {name: value is not None for name, value in self.as_dict().items()}
        )

    def as_dict(self) -> dict[str, Optional[float]]:
        """Return angle values keyed by their domain field names."""
        return {
            "left_knee_deg": self.left_knee_deg,
            "right_knee_deg": self.right_knee_deg,
            "left_hip_deg": self.left_hip_deg,
            "right_hip_deg": self.right_hip_deg,
            "left_ankle_deg": self.left_ankle_deg,
            "right_ankle_deg": self.right_ankle_deg,
            "trunk_angle_deg": self.trunk_angle_deg,
        }


@dataclass(frozen=True)
class BiomechanicalFrameResult:
    """Analysis output and preserved observations for one session frame.

    ``pose_ready`` means at least one side has enough valid angles for its
    hip-knee-ankle chain. It does not verify camera position, athlete
    orientation, or suitability for any particular view.
    """

    session: RecognitionSession
    frame_index: int
    timestamp_seconds: float
    angles: BiomechanicalAngles
    pose_detected: bool
    landmarks: Mapping[PoseLandmarkName, PoseLandmark2D] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.session, RecognitionSession):
            raise DomainInvariantError("session must be a RecognitionSession")
        if isinstance(self.frame_index, bool) or not isinstance(self.frame_index, int):
            raise DomainInvariantError("frame_index must be an integer")
        if self.frame_index < 0:
            raise DomainInvariantError("frame_index must be non-negative")
        if (
            isinstance(self.timestamp_seconds, bool)
            or not isinstance(self.timestamp_seconds, (int, float))
            or not math.isfinite(self.timestamp_seconds)
            or self.timestamp_seconds < 0
        ):
            raise DomainInvariantError(
                "timestamp_seconds must be a finite, non-negative number"
            )
        if not isinstance(self.angles, BiomechanicalAngles):
            raise DomainInvariantError("angles must be BiomechanicalAngles")
        if not isinstance(self.pose_detected, bool):
            raise DomainInvariantError("pose_detected must be a boolean")
        if not isinstance(self.landmarks, Mapping):
            raise DomainInvariantError("landmarks must be a mapping by anatomical name")
        preserved_landmarks = dict(self.landmarks)
        for name, landmark in preserved_landmarks.items():
            if not isinstance(name, PoseLandmarkName):
                raise DomainInvariantError("landmark keys must be PoseLandmarkName values")
            if not isinstance(landmark, PoseLandmark2D):
                raise DomainInvariantError(
                    "landmark {} must be a PoseLandmark2D".format(name.value)
                )
        object.__setattr__(self, "landmarks", MappingProxyType(preserved_landmarks))

    @property
    def pose_ready(self) -> bool:
        """Whether one complete lower-limb chain is usable for biomechanics.

        A usable side requires its hip, knee, and ankle angles. Given the
        angle rules, these also require shoulder, hip, knee, ankle, and foot
        landmarks to have met the analyzer's visibility threshold. Either
        side is sufficient; readiness makes no claim about camera view.
        """
        return any(
            all(value is not None for value in side_angles)
            for side_angles in (
                (
                    self.angles.left_hip_deg,
                    self.angles.left_knee_deg,
                    self.angles.left_ankle_deg,
                ),
                (
                    self.angles.right_hip_deg,
                    self.angles.right_knee_deg,
                    self.angles.right_ankle_deg,
                ),
            )
        )

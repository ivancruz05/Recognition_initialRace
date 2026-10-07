"""Infrastructure frame payload carrying optional cached pose observations."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Optional

from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName


@dataclass(frozen=True)
class AnalyzedFramePayload:
    """Original BGR image plus pose output already computed for live preview.

    ``pose_detected`` distinguishes a cached negative detection from an image
    that has not yet been passed through the detector (for example a file frame).
    The mapping is copied and made immutable to preserve the detector observation.
    """

    image: object = field(compare=False, repr=False)
    landmarks: Optional[Mapping[PoseLandmarkName, PoseLandmark2D]]
    pose_detected: bool = field(init=False)

    def __post_init__(self) -> None:
        landmarks = self.landmarks
        if self.image is None:
            raise ValueError("image must contain the original BGR frame")
        if landmarks is not None and not isinstance(landmarks, Mapping):
            raise TypeError("landmarks must be a mapping or None")
        object.__setattr__(self, "pose_detected", landmarks is not None)
        object.__setattr__(self, "landmarks", MappingProxyType(dict(landmarks or {})))

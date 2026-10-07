"""Model-independent anatomical landmark value objects."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from detection.domain.exceptions import DomainInvariantError


class PoseLandmarkName(Enum):
    """Anatomical point names independent of any pose model or identifier."""

    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"
    LEFT_ELBOW = "left_elbow"
    RIGHT_ELBOW = "right_elbow"
    LEFT_WRIST = "left_wrist"
    RIGHT_WRIST = "right_wrist"
    LEFT_HIP = "left_hip"
    RIGHT_HIP = "right_hip"
    LEFT_KNEE = "left_knee"
    RIGHT_KNEE = "right_knee"
    LEFT_ANKLE = "left_ankle"
    RIGHT_ANKLE = "right_ankle"
    LEFT_FOOT_INDEX = "left_foot_index"
    RIGHT_FOOT_INDEX = "right_foot_index"


@dataclass(frozen=True)
class PoseLandmark2D:
    """One normalized image-space point and its visibility in [0, 1].

    Coordinates and visibility are retained as returned by the adapter so a
    result can preserve the observations for later annotation. No model or
    camera calibration is implied by these values.
    """

    x: float
    y: float
    visibility: float

    def __post_init__(self) -> None:
        for name, value in (
            ("x", self.x),
            ("y", self.y),
            ("visibility", self.visibility),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise DomainInvariantError("{} must be a finite number".format(name))
        if self.visibility < 0 or self.visibility > 1:
            raise DomainInvariantError("visibility must be between 0 and 1")

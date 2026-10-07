"""Pure angle rules over anatomically named 2D pose landmarks.

The input contract is ``Mapping[PoseLandmarkName, PoseLandmark2D]``. Keys are
anatomical names, never model-specific numeric identifiers. An outer adapter
must translate its pose format into these names before calling the domain.
Coordinates use the source image's normalized x/y convention and are scaled
with the supplied image dimensions so non-square images preserve geometry.

Angles are unsigned internal angles in degrees (0..180). Knee and hip angles
are measured at their named joint; ankle angles use knee-ankle-foot-index. The
trunk angle is the unsigned lean from the image's vertical axis: 0 degrees is
upright. Missing/low-visibility points or degenerate segments produce None.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Callable, Optional, Tuple

from detection.domain.entities import BiomechanicalAngles
from detection.domain.exceptions import DomainInvariantError
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName


# Compatibility aliases for existing domain callers. These are enum members,
# not numeric model landmark IDs.
LEFT_SHOULDER = PoseLandmarkName.LEFT_SHOULDER
RIGHT_SHOULDER = PoseLandmarkName.RIGHT_SHOULDER
LEFT_HIP = PoseLandmarkName.LEFT_HIP
RIGHT_HIP = PoseLandmarkName.RIGHT_HIP
LEFT_KNEE = PoseLandmarkName.LEFT_KNEE
RIGHT_KNEE = PoseLandmarkName.RIGHT_KNEE
LEFT_ANKLE = PoseLandmarkName.LEFT_ANKLE
RIGHT_ANKLE = PoseLandmarkName.RIGHT_ANKLE
LEFT_FOOT_INDEX = PoseLandmarkName.LEFT_FOOT_INDEX
RIGHT_FOOT_INDEX = PoseLandmarkName.RIGHT_FOOT_INDEX


Point = Tuple[float, float]


def calculate_angle_at(
    first: Sequence[float], vertex: Sequence[float], last: Sequence[float]
) -> Optional[float]:
    """Return the unsigned angle at ``vertex`` or None for invalid geometry.

    This general pure rule is also used for joints that are not part of the
    fixed ``BiomechanicalAngles`` result, such as elbow angles in legacy views.
    """
    first_point = _validated_point(first, "first")
    vertex_point = _validated_point(vertex, "vertex")
    last_point = _validated_point(last, "last")
    return _joint_angle(first_point, vertex_point, last_point)


def calculate_biomechanical_angles(
    landmarks: Mapping[PoseLandmarkName, PoseLandmark2D],
    image_width: int,
    image_height: int,
    *,
    visibility_threshold: float = 0.5,
) -> BiomechanicalAngles:
    """Calculate bilateral joint angles and trunk lean from one 2D pose.

    ``landmarks`` must be keyed by :class:`PoseLandmarkName`; model-specific
    point identifiers must be translated at the adapter boundary. Visibility
    equal to the threshold is accepted. Angles depending on missing points
    remain unavailable without invalidating independent measurements.
    """
    if not isinstance(landmarks, Mapping):
        raise DomainInvariantError("landmarks must be a mapping by anatomical name")
    if any(not isinstance(name, PoseLandmarkName) for name in landmarks):
        raise DomainInvariantError("landmark keys must be PoseLandmarkName values")
    _require_image_dimension(image_width, "image_width")
    _require_image_dimension(image_height, "image_height")
    if (
        isinstance(visibility_threshold, bool)
        or not isinstance(visibility_threshold, (int, float))
        or not math.isfinite(visibility_threshold)
        or visibility_threshold < 0
        or visibility_threshold > 1
    ):
        raise DomainInvariantError("visibility_threshold must be between 0 and 1")

    def point(name: PoseLandmarkName) -> Optional[Point]:
        landmark = landmarks.get(name)
        if landmark is None:
            return None
        if not isinstance(landmark, PoseLandmark2D):
            raise DomainInvariantError(
                "landmark {} must be a PoseLandmark2D".format(name.value)
            )
        if landmark.visibility < visibility_threshold:
            return None
        return (landmark.x * image_width, landmark.y * image_height)

    left_knee = _joint_angle(
        point(PoseLandmarkName.LEFT_HIP),
        point(PoseLandmarkName.LEFT_KNEE),
        point(PoseLandmarkName.LEFT_ANKLE),
    )
    right_knee = _joint_angle(
        point(PoseLandmarkName.RIGHT_HIP),
        point(PoseLandmarkName.RIGHT_KNEE),
        point(PoseLandmarkName.RIGHT_ANKLE),
    )
    left_hip = _joint_angle(
        point(PoseLandmarkName.LEFT_SHOULDER),
        point(PoseLandmarkName.LEFT_HIP),
        point(PoseLandmarkName.LEFT_KNEE),
    )
    right_hip = _joint_angle(
        point(PoseLandmarkName.RIGHT_SHOULDER),
        point(PoseLandmarkName.RIGHT_HIP),
        point(PoseLandmarkName.RIGHT_KNEE),
    )
    left_ankle = _joint_angle(
        point(PoseLandmarkName.LEFT_KNEE),
        point(PoseLandmarkName.LEFT_ANKLE),
        point(PoseLandmarkName.LEFT_FOOT_INDEX),
    )
    right_ankle = _joint_angle(
        point(PoseLandmarkName.RIGHT_KNEE),
        point(PoseLandmarkName.RIGHT_ANKLE),
        point(PoseLandmarkName.RIGHT_FOOT_INDEX),
    )
    trunk = _trunk_angle(point)

    return BiomechanicalAngles(
        left_knee_deg=left_knee,
        right_knee_deg=right_knee,
        left_hip_deg=left_hip,
        right_hip_deg=right_hip,
        left_ankle_deg=left_ankle,
        right_ankle_deg=right_ankle,
        trunk_angle_deg=trunk,
    )


def _validated_point(value: Sequence[float], name: str) -> Point:
    if isinstance(value, (str, bytes)) or len(value) != 2:
        raise DomainInvariantError("{} must contain exactly two coordinates".format(name))
    coordinates = tuple(value)
    for coordinate in coordinates:
        if (
            isinstance(coordinate, bool)
            or not isinstance(coordinate, (int, float))
            or not math.isfinite(coordinate)
        ):
            raise DomainInvariantError("{} coordinates must be finite numbers".format(name))
    return (float(coordinates[0]), float(coordinates[1]))


def _require_image_dimension(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DomainInvariantError("{} must be a positive integer".format(name))


def _joint_angle(
    first: Optional[Point], vertex: Optional[Point], last: Optional[Point]
) -> Optional[float]:
    if first is None or vertex is None or last is None:
        return None

    first_vector = (first[0] - vertex[0], first[1] - vertex[1])
    last_vector = (last[0] - vertex[0], last[1] - vertex[1])
    first_length = math.hypot(first_vector[0], first_vector[1])
    last_length = math.hypot(last_vector[0], last_vector[1])
    if first_length == 0 or last_length == 0:
        return None

    cosine = (
        first_vector[0] * last_vector[0] + first_vector[1] * last_vector[1]
    ) / (first_length * last_length)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def _trunk_angle(
    point: Callable[[PoseLandmarkName], Optional[Point]],
) -> Optional[float]:
    side_segments = (
        (
            point(PoseLandmarkName.LEFT_SHOULDER),
            point(PoseLandmarkName.LEFT_HIP),
        ),
        (
            point(PoseLandmarkName.RIGHT_SHOULDER),
            point(PoseLandmarkName.RIGHT_HIP),
        ),
    )
    usable_segments = [
        (shoulder, hip)
        for shoulder, hip in side_segments
        if shoulder is not None and hip is not None
    ]
    if not usable_segments:
        return None

    shoulder_center = (
        sum(segment[0][0] for segment in usable_segments) / len(usable_segments),
        sum(segment[0][1] for segment in usable_segments) / len(usable_segments),
    )
    hip_center = (
        sum(segment[1][0] for segment in usable_segments) / len(usable_segments),
        sum(segment[1][1] for segment in usable_segments) / len(usable_segments),
    )
    dx = shoulder_center[0] - hip_center[0]
    dy = shoulder_center[1] - hip_center[1]
    if dx == 0 and dy == 0:
        return None
    return math.degrees(math.atan2(abs(dx), abs(dy)))

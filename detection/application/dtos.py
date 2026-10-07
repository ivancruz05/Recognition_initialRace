"""Input and output data transfer objects for recognition application use cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionProcessingRequest:
    """Identifiers for a manually initiated, single-athlete session."""

    session_id: str
    athlete_id: str


@dataclass(frozen=True)
class SessionProcessingResult:
    """Written-frame and pose-quality summary for a processed session.

    ``frames_pose_ready`` describes biomechanical angle availability only; it
    does not verify camera position or athlete orientation.
    """

    session_id: str
    frames_written: int
    frames_pose_detected: int
    frames_pose_ready: int

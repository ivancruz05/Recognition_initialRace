"""Ports used by application orchestration to inject recognition adapters."""

from __future__ import annotations

from typing import Optional, Protocol

from detection.domain.entities import (
    BiomechanicalFrameResult,
    CapturedFrame,
    RecognitionSession,
)


class FrameSource(Protocol):
    """Supplies timestamped frames from a live camera or a video file."""

    def start(self, session: RecognitionSession) -> None:
        """Begin reading frames for a manually started session."""
        ...

    def read_next(self) -> Optional[CapturedFrame]:
        """Return the next frame, or ``None`` when the source is exhausted."""
        ...

    def stop(self) -> None:
        """Stop reading frames when the user ends the session."""
        ...


class BiomechanicalAnalyzer(Protocol):
    """Analyzes one opaque source frame without prescribing an ML library."""

    def analyze(
        self, session: RecognitionSession, frame: CapturedFrame
    ) -> BiomechanicalFrameResult:
        """Return the biomechanical result associated with the input frame."""
        ...


class FrameResultWriter(Protocol):
    """Consumes per-frame results; an adapter may write CSV or another format."""

    def start(self, session: RecognitionSession) -> None:
        """Prepare output for a manually started session."""
        ...

    def write(self, result: BiomechanicalFrameResult) -> None:
        """Write one result row for one analyzed frame."""
        ...

    def stop(self) -> None:
        """Flush and close output when the session ends."""
        ...

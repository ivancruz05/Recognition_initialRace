"""Orchestrate frame capture, biomechanical analysis, and result writing."""

from enum import Enum
from threading import Event, Lock
from types import TracebackType
from typing import List, Optional

from detection.application.dtos import (
    SessionProcessingRequest,
    SessionProcessingResult,
)
from detection.domain.entities import RecognitionSession
from detection.domain.ports import BiomechanicalAnalyzer, FrameResultWriter, FrameSource


class SessionProcessorState(Enum):
    """Lifecycle states for a one-shot session processor."""

    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class RecognitionSessionProcessor:
    """Process frames for one manually started session.

    ``process`` owns the complete adapter lifecycle. ``stop`` requests a
    graceful stop; adapters are closed by ``process`` in its cleanup path.
    Instances are one-shot so that a completed or failed session cannot be
    accidentally started a second time with stale adapter state.
    """

    def __init__(
        self,
        frame_source: FrameSource,
        analyzer: BiomechanicalAnalyzer,
        result_writer: FrameResultWriter,
    ) -> None:
        self._frame_source = frame_source
        self._analyzer = analyzer
        self._result_writer = result_writer
        self._state = SessionProcessorState.READY
        self._state_lock = Lock()
        self._stop_requested = Event()
        self._frames_written = 0
        self._frames_pose_detected = 0
        self._frames_pose_ready = 0

    @property
    def state(self) -> SessionProcessorState:
        """Return the current lifecycle state."""
        with self._state_lock:
            return self._state

    @property
    def frames_written(self) -> int:
        """Return the number of successfully written frame results."""
        with self._state_lock:
            return self._frames_written

    @property
    def frames_pose_detected(self) -> int:
        """Return the number of written results with a detected pose."""
        with self._state_lock:
            return self._frames_pose_detected

    @property
    def frames_pose_ready(self) -> int:
        """Return the number of written results with a ready pose."""
        with self._state_lock:
            return self._frames_pose_ready

    def stop(self) -> None:
        """Request that the active session stop at the next frame boundary."""
        with self._state_lock:
            if self._state not in (
                SessionProcessorState.RUNNING,
                SessionProcessorState.STOPPING,
            ):
                raise RuntimeError("cannot stop a session that is not running")
            self._stop_requested.set()
            self._state = SessionProcessorState.STOPPING

    def process(
        self, request: SessionProcessingRequest
    ) -> SessionProcessingResult:
        """Start adapters and process each available frame until stopped/exhausted."""
        session = RecognitionSession(
            session_id=request.session_id,
            athlete_id=request.athlete_id,
        )
        with self._state_lock:
            if self._state is not SessionProcessorState.READY:
                raise RuntimeError("a session processor can only be started once")
            self._frames_written = 0
            self._frames_pose_detected = 0
            self._frames_pose_ready = 0
            self._state = SessionProcessorState.RUNNING

        source_start_attempted = False
        writer_start_attempted = False
        processing_error: Optional[BaseException] = None
        cleanup_errors: List[BaseException] = []

        try:
            source_start_attempted = True
            self._frame_source.start(session)

            while not self._stop_requested.is_set():
                frame = self._frame_source.read_next()
                if frame is None or self._stop_requested.is_set():
                    break

                if not writer_start_attempted:
                    writer_start_attempted = True
                    self._result_writer.start(session)

                result = self._analyzer.analyze(session, frame)
                self._result_writer.write(result)
                with self._state_lock:
                    self._frames_written += 1
                    if result.pose_detected:
                        self._frames_pose_detected += 1
                    if result.pose_ready:
                        self._frames_pose_ready += 1
        except BaseException as error:
            processing_error = error
        finally:
            # Stop in reverse startup order, and always attempt both cleanups.
            if writer_start_attempted:
                try:
                    self._result_writer.stop()
                except BaseException as error:
                    cleanup_errors.append(error)
            if source_start_attempted:
                try:
                    self._frame_source.stop()
                except BaseException as error:
                    cleanup_errors.append(error)

            with self._state_lock:
                if processing_error is not None or cleanup_errors:
                    self._state = SessionProcessorState.FAILED
                else:
                    self._state = SessionProcessorState.STOPPED

        # Keep the original processing exception primary if cleanup also fails.
        if processing_error is not None:
            traceback: Optional[TracebackType] = processing_error.__traceback__
            raise processing_error.with_traceback(traceback)
        if cleanup_errors:
            raise cleanup_errors[0]

        return SessionProcessingResult(
            session_id=session.session_id,
            frames_written=self.frames_written,
            frames_pose_detected=self.frames_pose_detected,
            frames_pose_ready=self.frames_pose_ready,
        )

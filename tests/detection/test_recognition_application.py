"""Application unit tests with in-memory port fakes only."""

import pytest

from detection.application import (
    RecognitionSessionProcessor,
    SessionProcessingRequest,
    SessionProcessorState,
)
from detection.domain.entities import (
    BiomechanicalAngles,
    BiomechanicalFrameResult,
    RecognitionSession,
)
from tests.detection.recognition_factories import CapturedFrameFactory


class FakeFrameSource:
    def __init__(self, frames=(), start_error=None, stop_error=None):
        self.frames = list(frames)
        self.start_error = start_error
        self.stop_error = stop_error
        self.events = []

    def start(self, session):
        self.events.append(("start", session))
        if self.start_error:
            raise self.start_error

    def read_next(self):
        self.events.append(("read",))
        return self.frames.pop(0) if self.frames else None

    def stop(self):
        self.events.append(("stop",))
        if self.stop_error:
            raise self.stop_error


class FakeAnalyzer:
    def __init__(self, error=None, on_analyze=None, results=None):
        self.error = error
        self.on_analyze = on_analyze
        self.results = list(results or [])
        self.frames = []

    def analyze(self, session, frame):
        self.frames.append(frame)
        if self.on_analyze:
            self.on_analyze()
        if self.error:
            raise self.error
        if self.results:
            return self.results.pop(0)
        return BiomechanicalFrameResult(
            session=session,
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            angles=BiomechanicalAngles(left_knee_deg=90.0),
            pose_detected=True,
        )


class FakeWriter:
    def __init__(self, start_error=None, write_error=None, stop_error=None):
        self.start_error = start_error
        self.write_error = write_error
        self.stop_error = stop_error
        self.events = []
        self.results = []

    def start(self, session):
        self.events.append(("start", session))
        if self.start_error:
            raise self.start_error

    def write(self, result):
        self.events.append(("write", result))
        if self.write_error:
            raise self.write_error
        self.results.append(result)

    def stop(self):
        self.events.append(("stop",))
        if self.stop_error:
            raise self.stop_error


def _processor(frames=(), **kwargs):
    source = kwargs.pop("source", FakeFrameSource(frames))
    analyzer = kwargs.pop("analyzer", FakeAnalyzer())
    writer = kwargs.pop("writer", FakeWriter())
    return RecognitionSessionProcessor(source, analyzer, writer), source, analyzer, writer


def test_process_counts_detected_and_ready_frames_without_dropping_unready_frames():
    frames = [CapturedFrameFactory(frame_index=i, timestamp_seconds=i / 10.0) for i in range(3)]
    source = FakeFrameSource(frames)
    session = RecognitionSession(session_id="s-1", athlete_id="a-1")
    results = [
        BiomechanicalFrameResult(
            session=session,
            frame_index=0,
            timestamp_seconds=0.0,
            angles=BiomechanicalAngles(left_knee_deg=90.0),
            pose_detected=False,
        ),
        BiomechanicalFrameResult(
            session=session,
            frame_index=1,
            timestamp_seconds=0.1,
            angles=BiomechanicalAngles(left_hip_deg=90, left_knee_deg=90, left_ankle_deg=90),
            pose_detected=True,
        ),
        BiomechanicalFrameResult(
            session=session,
            frame_index=2,
            timestamp_seconds=0.2,
            angles=BiomechanicalAngles(right_hip_deg=90, right_knee_deg=90, right_ankle_deg=90),
            pose_detected=True,
        ),
    ]
    analyzer = FakeAnalyzer(results=results)
    writer = FakeWriter()
    processor = RecognitionSessionProcessor(source, analyzer, writer)

    result = processor.process(SessionProcessingRequest("s-1", "a-1"))

    assert result.session_id == "s-1"
    assert result.frames_written == 3
    assert result.frames_pose_detected == 2
    assert result.frames_pose_ready == 2
    assert len(analyzer.frames) == len(writer.results) == 3
    assert [event[0] for event in writer.events] == ["start", "write", "write", "write", "stop"]
    assert [event[0] for event in source.events][-1] == "stop"
    assert source.events[0][1] == writer.events[0][1]
    assert processor.state is SessionProcessorState.STOPPED


def test_stop_request_finishes_after_current_frame_and_processor_is_one_shot():
    processor, source, analyzer, writer = _processor(
        [CapturedFrameFactory(frame_index=i) for i in range(4)]
    )
    analyzer.on_analyze = processor.stop

    result = processor.process(SessionProcessingRequest("s-stop", "a-1"))

    assert result.frames_written == 1
    assert processor.state is SessionProcessorState.STOPPED
    with pytest.raises(RuntimeError, match="only be started once"):
        processor.process(SessionProcessingRequest("s-again", "a-1"))
    with pytest.raises(RuntimeError, match="not running"):
        processor.stop()


def test_stop_during_preview_without_a_frame_does_not_start_or_stop_writer():
    source = FakeFrameSource()
    writer = FakeWriter()
    processor = RecognitionSessionProcessor(source, FakeAnalyzer(), writer)
    source.read_next = lambda: (processor.stop(), None)[1]

    result = processor.process(SessionProcessingRequest("s-preview", "a-1"))

    assert result.frames_written == 0
    assert writer.events == []
    assert [event[0] for event in source.events] == ["start", "stop"]
    assert processor.state is SessionProcessorState.STOPPED


@pytest.mark.parametrize("failure_location", ["read", "analyze", "write"])
def test_processing_exceptions_propagate_and_all_started_adapters_close(failure_location):
    failure = ValueError("failed at " + failure_location)
    source = FakeFrameSource([CapturedFrameFactory()])
    analyzer = FakeAnalyzer(error=failure if failure_location == "analyze" else None)
    writer = FakeWriter(write_error=failure if failure_location == "write" else None)
    if failure_location == "read":
        source.read_next = lambda: (_ for _ in ()).throw(failure)
    processor = RecognitionSessionProcessor(source, analyzer, writer)

    with pytest.raises(ValueError, match=failure_location):
        processor.process(SessionProcessingRequest("s-error", "a-1"))

    if failure_location == "read":
        # The first frame was never obtained, so lazy writer startup was not attempted.
        assert writer.events == []
    else:
        assert [event[0] for event in writer.events][-1] == "stop"
    assert source.events[-1][0] == "stop"
    assert processor.state is SessionProcessorState.FAILED


def test_source_start_failure_still_attempts_source_cleanup_but_not_writer():
    source = FakeFrameSource(start_error=RuntimeError("source start"))
    writer = FakeWriter()
    processor = RecognitionSessionProcessor(source, FakeAnalyzer(), writer)

    with pytest.raises(RuntimeError, match="source start"):
        processor.process(SessionProcessingRequest("s", "a"))

    assert [event[0] for event in source.events] == ["start", "stop"]
    assert writer.events == []
    assert processor.state is SessionProcessorState.FAILED


def test_writer_start_failure_still_closes_both_adapters():
    source = FakeFrameSource([CapturedFrameFactory()])
    writer = FakeWriter(start_error=RuntimeError("writer start"))
    processor = RecognitionSessionProcessor(source, FakeAnalyzer(), writer)

    with pytest.raises(RuntimeError, match="writer start"):
        processor.process(SessionProcessingRequest("s", "a"))

    assert [event[0] for event in source.events] == ["start", "read", "stop"]
    assert [event[0] for event in writer.events] == ["start", "stop"]
    assert processor.state is SessionProcessorState.FAILED


def test_cleanup_failures_do_not_prevent_other_cleanup_and_mark_failed():
    source = FakeFrameSource(
        [CapturedFrameFactory()], stop_error=RuntimeError("source close")
    )
    writer = FakeWriter(stop_error=RuntimeError("writer close"))
    processor = RecognitionSessionProcessor(source, FakeAnalyzer(), writer)

    with pytest.raises(RuntimeError, match="writer close"):
        processor.process(SessionProcessingRequest("s", "a"))

    assert writer.events[-1][0] == "stop"
    assert source.events[-1][0] == "stop"
    assert processor.state is SessionProcessorState.FAILED


def test_processing_exception_remains_primary_when_cleanup_also_fails():
    source = FakeFrameSource(
        [CapturedFrameFactory()], stop_error=RuntimeError("source close")
    )
    writer = FakeWriter(stop_error=RuntimeError("writer close"))
    analyzer = FakeAnalyzer(error=ValueError("analyzer failure"))
    processor = RecognitionSessionProcessor(source, analyzer, writer)

    with pytest.raises(ValueError, match="analyzer failure"):
        processor.process(SessionProcessingRequest("s", "a"))

    assert processor.state is SessionProcessorState.FAILED


def test_invalid_request_does_not_consume_one_shot_processor():
    processor, _, _, _ = _processor()

    with pytest.raises(ValueError, match="session_id"):
        processor.process(SessionProcessingRequest("", "a"))

    assert processor.state is SessionProcessorState.READY
    result = processor.process(SessionProcessingRequest("s", "a"))
    assert result.frames_written == 0

"""CLI contract tests; execution is stubbed before detector construction."""

from click.testing import CliRunner
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from detection import local_cli
from detection.domain.entities import BiomechanicalAngles, BiomechanicalFrameResult
from tests.detection.recognition_factories import CapturedFrameFactory


class SessionFrameSource:
    """In-memory source fake with optional read failures and partial MP4 output."""

    def __init__(
        self,
        frames=(),
        *,
        read_error=None,
        stop_error=None,
        raw_video_path=None,
        raw_count=0,
    ):
        self.frames = list(frames)
        self.read_error = read_error
        self.stop_error = stop_error
        self.raw_video_path = raw_video_path
        self.raw_video_frames_written = raw_count
        self.events = []

    def start(self, _session):
        self.events.append("source.start")

    def read_next(self):
        self.events.append("source.read")
        if self.frames:
            frame = self.frames.pop(0)
            if self.raw_video_path is not None:
                Path(self.raw_video_path).write_bytes(b"partial mp4")
            return frame
        if self.read_error is not None:
            raise self.read_error
        return None

    def stop(self):
        self.events.append("source.stop")
        if self.stop_error is not None:
            raise self.stop_error


class SessionAnalyzer:
    def __init__(self, error_on_second_frame=None):
        self.error_on_second_frame = error_on_second_frame
        self.frames_seen = 0

    def analyze(self, session, frame):
        self.frames_seen += 1
        if self.frames_seen == 2 and self.error_on_second_frame is not None:
            raise self.error_on_second_frame
        return BiomechanicalFrameResult(
            session=session,
            frame_index=frame.frame_index,
            timestamp_seconds=frame.timestamp_seconds,
            angles=BiomechanicalAngles(
                left_hip_deg=90.0,
                left_knee_deg=90.0,
                left_ankle_deg=90.0,
            ),
            pose_detected=True,
        )


class SessionDetector:
    def __init__(self, events, manifest_path=None):
        self.events = events
        self.manifest_path = manifest_path

    def close(self):
        self.events.append("detector.close")
        if self.manifest_path is not None:
            assert json.loads(self.manifest_path.read_text(encoding="utf-8"))["status"] == "in_progress"


def _install_session_fakes(
    monkeypatch,
    *,
    source_factory,
    events,
    manifest_path=None,
    analyzer_error=None,
):
    detector = SessionDetector(events, manifest_path)
    monkeypatch.setattr(local_cli, "MediaPipePoseDetector", lambda: (events.append("detector.start") or detector))
    monkeypatch.setattr(
        local_cli,
        "MediaPipeBiomechanicalAnalyzer",
        lambda _detector: SessionAnalyzer(analyzer_error),
    )
    monkeypatch.setattr(local_cli, "OpenCVVideoFileFrameSource", source_factory)
    monkeypatch.setattr(local_cli.click, "echo", lambda _message: None)
    return detector


def test_cli_help_lists_local_capture_and_video_commands():
    runner = CliRunner()

    result = runner.invoke(local_cli.cli, ["--help"])

    assert result.exit_code == 0
    assert "capture" in result.output
    assert "analyze-video" in result.output
    assert "Results are written as CSV" in result.output


def test_capture_help_documents_manual_preview_controls():
    result = CliRunner().invoke(local_cli.cli, ["capture", "--help"])

    assert result.exit_code == 0
    assert "--camera-index" in result.output
    assert "press t to start" in result.output
    assert "--athlete-id" in result.output
    assert "--camera-height-cm" in result.output
    assert "100.0" in result.output


def test_analyze_video_rejects_a_missing_file_before_constructing_detector(tmp_path):
    result = CliRunner().invoke(
        local_cli.cli,
        [
            "analyze-video",
            str(tmp_path / "not-here.mp4"),
            "--athlete-id",
            "athlete-1",
            "--output",
            str(tmp_path / "result.csv"),
        ],
    )

    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_output_must_be_csv_for_both_commands():
    runner = CliRunner()
    capture = runner.invoke(
        local_cli.cli,
        ["capture", "--camera-index", "0", "--athlete-id", "a", "--output", "out.txt"],
    )
    video = runner.invoke(
        local_cli.cli,
        ["analyze-video", __file__, "--athlete-id", "a", "--output", "out.txt"],
    )

    assert capture.exit_code == 2
    assert video.exit_code == 2
    assert "output path must end in .csv" in capture.output
    assert "output path must end in .csv" in video.output


def test_analyze_video_wires_file_and_metadata_to_session_runner(tmp_path, monkeypatch):
    video_path = tmp_path / "sprint.mov"
    video_path.touch()
    source = object()
    monkeypatch.setattr(local_cli, "OpenCVVideoFileFrameSource", lambda path: (path, source))
    calls = []
    monkeypatch.setattr(local_cli, "_run_session", lambda **kwargs: calls.append(kwargs) or 2)

    result = CliRunner().invoke(
        local_cli.cli,
        [
            "analyze-video",
            str(video_path),
            "--athlete-id",
            "runner-8",
            "--session-id",
            "manual-session",
            "--output",
            str(tmp_path / "angles.csv"),
            "--camera-height-cm",
            "112.5",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0]["athlete_id"] == "runner-8"
    assert calls[0]["session_id"] == "manual-session"
    assert calls[0]["output"] == str(tmp_path / "angles.csv")
    assert calls[0]["capture_metadata"] == {
        "capture_source": "video_file",
        "source_reference": "sprint.mov",
        "camera_index": "",
        "expected_view": "lateral",
        "camera_height_cm": 112.5,
    }
    assert "frame_source_factory" in calls[0]
    assert "raw_video_path" not in calls[0]
    assert calls[0]["frame_source_factory"](object()) == (str(video_path), source)


def test_capture_wires_camera_index_and_resolves_missing_session_id(tmp_path, monkeypatch):
    monkeypatch.setattr(local_cli, "_resolve_session_id", lambda value: value or "generated-id")
    calls = []
    monkeypatch.setattr(local_cli, "_run_session", lambda **kwargs: calls.append(kwargs) or 1)

    result = CliRunner().invoke(
        local_cli.cli,
        [
            "capture",
            "--camera-index",
            "3",
            "--athlete-id",
            "runner-2",
            "--output",
            str(tmp_path / "capture.csv"),
            "--camera-height-cm",
            "108.25",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    assert calls[0]["athlete_id"] == "runner-2"
    assert calls[0]["session_id"] == "generated-id"
    assert calls[0]["output"] == str(tmp_path / "capture.csv")
    assert calls[0]["raw_video_path"] == str(tmp_path / "capture.mp4")
    assert calls[0]["capture_metadata"] == {
        "capture_source": "live_camera",
        "source_reference": "capture.mp4",
        "camera_index": 3,
        "expected_view": "lateral",
        "camera_height_cm": 108.25,
    }
    assert "frame_source_factory" in calls[0]
    assert "Camera preview controls" in result.output


def test_capture_rejects_preexisting_default_video_output_without_starting_session(
    tmp_path, monkeypatch
):
    output = tmp_path / "capture.csv"
    video_output = tmp_path / "capture.mp4"
    video_output.touch()
    calls = []
    monkeypatch.setattr(local_cli, "_run_session", lambda **kwargs: calls.append(kwargs))

    result = CliRunner().invoke(
        local_cli.cli,
        ["capture", "--camera-index", "0", "--athlete-id", "a", "--output", str(output)],
    )

    assert result.exit_code == 1
    assert "video output file already exists" in result.output
    assert calls == []


def test_capture_accepts_explicit_distinct_video_output(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(local_cli, "_run_session", lambda **kwargs: calls.append(kwargs))
    output = tmp_path / "angles.csv"
    raw_video = tmp_path / "unannotated.mp4"

    result = CliRunner().invoke(
        local_cli.cli,
        [
            "capture", "--camera-index", "1", "--athlete-id", "a",
            "--output", str(output), "--video-output", str(raw_video),
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls[0]["raw_video_path"] == str(raw_video)


def test_capture_requires_csv_output_and_rejects_existing_csv(tmp_path):
    runner = CliRunner()
    required = runner.invoke(local_cli.cli, ["capture", "--camera-index", "0", "--athlete-id", "a"])
    existing = tmp_path / "existing.csv"
    existing.touch()
    collision = runner.invoke(
        local_cli.cli,
        ["capture", "--camera-index", "0", "--athlete-id", "a", "--output", str(existing)],
    )

    assert required.exit_code == 2
    assert "--output" in required.output
    assert collision.exit_code == 2
    assert "already exists" in collision.output


def test_cli_rejects_csv_and_video_output_when_parent_directory_is_missing(tmp_path):
    missing_parent = tmp_path / "not-created"
    runner = CliRunner()
    capture = runner.invoke(
        local_cli.cli,
        [
            "capture", "--camera-index", "0", "--athlete-id", "a",
            "--output", str(missing_parent / "capture.csv"),
        ],
    )
    video = runner.invoke(
        local_cli.cli,
        [
            "capture", "--camera-index", "0", "--athlete-id", "a",
            "--output", str(tmp_path / "valid.csv"),
            "--video-output", str(missing_parent / "capture.mp4"),
        ],
    )
    analyze = runner.invoke(
        local_cli.cli,
        [
            "analyze-video", __file__, "--athlete-id", "a",
            "--output", str(missing_parent / "result.csv"),
        ],
    )

    assert capture.exit_code == 2
    assert "output directory does not exist" in capture.output
    assert video.exit_code == 2
    assert "video output directory does not exist" in video.output
    assert analyze.exit_code == 2
    assert "output directory does not exist" in analyze.output
    assert not missing_parent.exists()


@pytest.mark.parametrize("height", ["0", "-1", "nan", "inf"])
def test_capture_rejects_non_positive_or_non_finite_camera_height(tmp_path, height):
    result = CliRunner().invoke(
        local_cli.cli,
        [
            "capture", "--camera-index", "0", "--athlete-id", "a",
            "--output", str(tmp_path / "capture.csv"),
            "--camera-height-cm", height,
        ],
    )

    assert result.exit_code == 2
    assert "camera height" in result.output or "not in the range" in result.output


def test_run_session_composes_application_and_infrastructure_and_closes_detector(
    tmp_path, monkeypatch
):
    events = []
    output_messages = []

    class FakeDetector:
        def close(self):
            events.append("detector.close")

    class FakeProcessor:
        def __init__(self, frame_source, analyzer, result_writer):
            events.append(("processor.init", frame_source, analyzer, result_writer))

        def process(self, request):
            events.append(("processor.process", request))
            return SimpleNamespace(
                session_id=request.session_id,
                frames_written=3,
                frames_pose_detected=2,
                frames_pose_ready=1,
            )

    detector = FakeDetector()
    analyzer_marker = object()
    writer_marker = object()
    source = object()
    monkeypatch.setattr(local_cli, "MediaPipePoseDetector", lambda: detector)
    monkeypatch.setattr(
        local_cli,
        "MediaPipeBiomechanicalAnalyzer",
        lambda actual_detector: (events.append(("analyzer.init", actual_detector)) or analyzer_marker),
    )
    monkeypatch.setattr(
        local_cli,
        "CSVFrameResultWriter",
        lambda output: (events.append(("writer.init", output)) or writer_marker),
    )
    monkeypatch.setattr(local_cli, "RecognitionSessionProcessor", FakeProcessor)
    monkeypatch.setattr(local_cli.click, "echo", output_messages.append)

    def make_source(shared_detector):
        events.append(("source.factory", shared_detector))
        return source

    count = local_cli._run_session(
        athlete_id="runner-3",
        session_id="session-3",
        output=str(tmp_path / "angles.csv"),
        frame_source_factory=make_source,
    )

    assert count == 3
    assert events[0] == ("source.factory", detector)
    assert events[1] == ("analyzer.init", detector)
    assert events[2] == ("writer.init", str(tmp_path / "angles.csv"))
    assert events[3] == ("processor.init", source, analyzer_marker, writer_marker)
    assert events[4][0] == "processor.process"
    assert events[4][1].session_id == "session-3"
    assert events[4][1].athlete_id == "runner-3"
    assert events[5] == "detector.close"
    assert output_messages[0] == (
        "Session session-3 complete: 3 total frames written; 2 poses detected; "
        "1 pose-ready frames."
    )
    assert output_messages[1] == "CSV: {}".format(tmp_path / "angles.csv")
    assert len([event for event in events if event == "detector.close"]) == 1


def test_run_session_finalizes_complete_only_after_detector_is_closed(tmp_path, monkeypatch):
    output = tmp_path / "angles.csv"
    raw_video = tmp_path / "capture.mp4"
    manifest_path = tmp_path / "angles.manifest.json"
    events = []
    source = SessionFrameSource(
        [CapturedFrameFactory()], raw_video_path=raw_video, raw_count=1
    )
    _install_session_fakes(
        monkeypatch,
        source_factory=lambda _detector: source,
        events=events,
        manifest_path=manifest_path,
    )

    written = local_cli._run_session(
        athlete_id="runner-1",
        session_id="session-1",
        output=str(output),
        frame_source_factory=lambda detector: (events.append("source.factory") or source),
        raw_video_path=str(raw_video),
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert written == 1
    assert manifest["status"] == "complete"
    assert manifest["frames_written"] == 1
    assert manifest["pose_detected"] == 1
    assert manifest["pose_ready"] == 1
    assert manifest["raw_video_frames_written"] == 1
    assert raw_video.read_bytes() == b"partial mp4"
    assert output.exists()
    assert events.index("detector.close") > events.index("detector.start")
    assert source.events[-1] == "source.stop"


def test_cancel_before_first_frame_finalizes_empty_without_csv_or_mp4(tmp_path, monkeypatch):
    output = tmp_path / "cancelled.csv"
    raw_video = tmp_path / "cancelled.mp4"
    manifest_path = tmp_path / "cancelled.manifest.json"
    events = []
    source = SessionFrameSource()
    _install_session_fakes(
        monkeypatch,
        source_factory=lambda _detector: source,
        events=events,
        manifest_path=manifest_path,
    )

    count = local_cli._run_session(
        athlete_id="runner-1",
        session_id="cancelled",
        output=str(output),
        frame_source_factory=lambda _detector: source,
        raw_video_path=str(raw_video),
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert count == 0
    assert manifest["status"] == "empty"
    assert manifest["frames_written"] == manifest["raw_video_frames_written"] == 0
    assert manifest["pose_detected"] == manifest["pose_ready"] == 0
    assert not output.exists()
    assert not raw_video.exists()
    assert source.events[-1] == "source.stop"


@pytest.mark.parametrize("failure_stage", ["read", "processing"])
def test_session_error_records_partial_counts_and_mp4_but_reraises_original_error(
    tmp_path, monkeypatch, failure_stage
):
    output = tmp_path / "partial.csv"
    raw_video = tmp_path / "partial.mp4"
    manifest_path = tmp_path / "partial.manifest.json"
    failure = OSError("camera read failed")
    frames = [CapturedFrameFactory()]
    if failure_stage == "processing":
        frames.append(CapturedFrameFactory(frame_index=1, timestamp_seconds=0.1))
    source = SessionFrameSource(
        frames,
        read_error=failure if failure_stage == "read" else None,
        raw_video_path=raw_video,
        raw_count=2,
    )
    events = []
    _install_session_fakes(
        monkeypatch,
        source_factory=lambda _detector: source,
        events=events,
        manifest_path=manifest_path,
        analyzer_error=failure if failure_stage == "processing" else None,
    )

    with pytest.raises(OSError) as caught:
        local_cli._run_session(
            athlete_id="runner-1",
            session_id="partial",
            output=str(output),
            frame_source_factory=lambda _detector: source,
            raw_video_path=str(raw_video),
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert caught.value is failure
    assert manifest["status"] == "failed"
    assert manifest["frames_written"] == 1
    assert manifest["pose_detected"] == 1
    assert manifest["pose_ready"] == 1
    assert manifest["raw_video_frames_written"] == 2
    assert manifest["error_type"] == "OSError"
    assert manifest["error_message"] == "camera read failed"
    assert output.exists()
    assert raw_video.read_bytes() == b"partial mp4"
    assert events[-1] == "detector.close"


def test_raw_video_writer_verification_error_marks_manifest_failed_and_keeps_mp4(
    tmp_path, monkeypatch
):
    output = tmp_path / "writer-error.csv"
    raw_video = tmp_path / "writer-error.mp4"
    manifest_path = tmp_path / "writer-error.manifest.json"
    failure = RuntimeError("raw video verification decoded no frames")
    source = SessionFrameSource(
        [CapturedFrameFactory()],
        stop_error=failure,
        raw_video_path=raw_video,
        raw_count=1,
    )
    events = []
    _install_session_fakes(
        monkeypatch,
        source_factory=lambda _detector: source,
        events=events,
        manifest_path=manifest_path,
    )

    with pytest.raises(RuntimeError, match="raw video verification decoded no frames"):
        local_cli._run_session(
            athlete_id="runner-1",
            session_id="writer-error",
            output=str(output),
            frame_source_factory=lambda _detector: source,
            raw_video_path=str(raw_video),
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["frames_written"] == 1
    assert manifest["raw_video_frames_written"] == 1
    assert manifest["error_type"] == "RuntimeError"
    assert manifest["error_message"] == str(failure)
    assert raw_video.read_bytes() == b"partial mp4"
    assert output.exists()


def test_csv_writer_close_error_marks_manifest_failed_and_keeps_partial_csv(
    tmp_path, monkeypatch
):
    output = tmp_path / "csv-error.csv"
    manifest_path = tmp_path / "csv-error.manifest.json"
    failure = OSError("CSV flush failed")
    events = []
    source = SessionFrameSource([CapturedFrameFactory()])

    class BrokenCSVWriter:
        def __init__(self, path):
            self.path = Path(path)
            self.rows_written = 0

        def start(self, _session):
            self.path.write_text("partial CSV header\n", encoding="utf-8")

        def write(self, _result):
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write("partial CSV row\n")
            self.rows_written += 1

        def stop(self):
            raise failure

    _install_session_fakes(
        monkeypatch,
        source_factory=lambda _detector: source,
        events=events,
        manifest_path=manifest_path,
    )
    monkeypatch.setattr(local_cli, "CSVFrameResultWriter", BrokenCSVWriter)

    with pytest.raises(OSError, match="CSV flush failed"):
        local_cli._run_session(
            athlete_id="runner-1",
            session_id="csv-error",
            output=str(output),
            frame_source_factory=lambda _detector: source,
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["frames_written"] == 1
    assert manifest["error_type"] == "OSError"
    assert manifest["error_message"] == "CSV flush failed"
    assert output.read_text(encoding="utf-8") == "partial CSV header\npartial CSV row\n"


@pytest.mark.parametrize("collision", ["csv", "manifest", "raw_mp4"])
def test_existing_artifact_collision_is_rejected_before_detector_or_source_start(
    tmp_path, monkeypatch, collision
):
    output = tmp_path / "collision.csv"
    manifest = tmp_path / "collision.manifest.json"
    raw_video = tmp_path / "collision.mp4"
    if collision == "csv":
        output.touch()
    elif collision == "manifest":
        manifest.write_text("{}", encoding="utf-8")
    else:
        raw_video.touch()

    detector_starts = []
    source_starts = []
    monkeypatch.setattr(
        local_cli,
        "MediaPipePoseDetector",
        lambda: detector_starts.append(True),
    )

    with pytest.raises(local_cli.click.ClickException):
        local_cli._run_session(
            athlete_id="runner-1",
            session_id="collision",
            output=str(output),
            frame_source_factory=lambda _detector: source_starts.append(True),
            raw_video_path=str(raw_video),
        )

    assert detector_starts == []
    assert source_starts == []


@pytest.mark.parametrize("artifact", ["csv", "manifest"])
def test_raw_mp4_path_must_not_alias_csv_or_manifest_before_detector_start(
    tmp_path, monkeypatch, artifact
):
    output = tmp_path / "alias.csv"
    raw_video = output if artifact == "csv" else tmp_path / "alias.manifest.json"
    detector_starts = []
    source_starts = []
    monkeypatch.setattr(
        local_cli,
        "MediaPipePoseDetector",
        lambda: detector_starts.append(True),
    )

    with pytest.raises(local_cli.click.ClickException, match="must be different files"):
        local_cli._run_session(
            athlete_id="runner-1",
            session_id="alias",
            output=str(output),
            frame_source_factory=lambda _detector: source_starts.append(True),
            raw_video_path=str(raw_video),
        )

    assert detector_starts == []
    assert source_starts == []
    assert not output.exists()


def test_analyze_video_manifest_uses_input_basename_and_has_no_raw_mp4(
    tmp_path, monkeypatch
):
    video_path = tmp_path / "source-video.mov"
    video_path.touch()
    output = tmp_path / "analysis.csv"
    manifest_path = tmp_path / "analysis.manifest.json"
    events = []
    source = SessionFrameSource()
    _install_session_fakes(
        monkeypatch,
        source_factory=lambda _detector: source,
        events=events,
        manifest_path=manifest_path,
    )
    source_paths = []
    monkeypatch.setattr(
        local_cli,
        "OpenCVVideoFileFrameSource",
        lambda path: (source_paths.append(path) or source),
    )

    result = CliRunner().invoke(
        local_cli.cli,
        [
            "analyze-video",
            str(video_path),
            "--athlete-id",
            "runner-1",
            "--session-id",
            "video-session",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert source_paths == [str(video_path)]
    assert manifest["status"] == "empty"
    assert manifest["source_reference"] == "source-video.mov"
    assert manifest["raw_mp4"] is None
    assert manifest["capture_metadata"]["source_reference"] == "source-video.mov"

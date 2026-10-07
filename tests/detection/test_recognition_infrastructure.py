"""Adapter tests with fake OpenCV, fake detector, and filesystem temp paths."""

import csv
import io
import sys
import types

import pytest

from detection.domain.entities import BiomechanicalAngles
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName
from detection.infrastructure.camera_source import OpenCVCameraFrameSource
from detection.infrastructure.csv_result_writer import CSVFrameResultWriter
from detection.infrastructure.frame_payload import AnalyzedFramePayload
from detection.infrastructure.mediapipe_analyzer import MediaPipeBiomechanicalAnalyzer
from detection.infrastructure.mediapipe_pose_detector import MediaPipePoseDetector
from detection.infrastructure.raw_video_writer import OpenCVRawVideoWriter
from detection.infrastructure.video_file_source import OpenCVVideoFileFrameSource
from tests.detection.recognition_factories import (
    BiomechanicalFrameResultFactory,
    PoseLandmark2DFactory,
    RecognitionSessionFactory,
)


class FakeCapture:
    def __init__(self, frames=(), opened=True, fps=20.0):
        self.frames = list(frames)
        self.opened = opened
        self.fps = fps
        self.releases = 0

    def isOpened(self):
        return self.opened

    def get(self, _property):
        return self.fps

    def read(self):
        return self.frames.pop(0) if self.frames else (False, None)

    def release(self):
        self.releases += 1


class FakeCV2(types.ModuleType):
    WINDOW_NORMAL = 0
    CAP_PROP_FPS = 5
    FONT_HERSHEY_SIMPLEX = 7
    COLOR_BGR2RGB = 6

    def __init__(self, capture, keys=()):
        super().__init__("cv2")
        self.capture = capture
        self.keys = list(keys)
        self.video_capture_calls = []
        self.windows = []
        self.shown = []
        self.destroyed = []
        self.color_conversions = []
        self.draw_calls = []

    def cvtColor(self, image, code):
        converted = ("rgb", image)
        self.color_conversions.append((image, code, converted))
        return converted

    def VideoCapture(self, *args):
        self.video_capture_calls.append(args)
        return self.capture

    def namedWindow(self, name, mode):
        self.windows.append((name, mode))

    def imshow(self, name, image):
        self.shown.append((name, image))

    def waitKey(self, _delay):
        return self.keys.pop(0) if self.keys else -1

    def destroyWindow(self, name):
        self.destroyed.append(name)

    def line(self, image, *args):
        self.draw_calls.append(("line", image, args))

    def circle(self, image, *args):
        self.draw_calls.append(("circle", image, args))

    def putText(self, image, text, *args):
        self.draw_calls.append(("text", image, text, args))


def _install_cv2(monkeypatch, capture, keys=()):
    module = FakeCV2(capture, keys)
    monkeypatch.setitem(sys.modules, "cv2", module)
    return module


def test_csv_writer_emits_header_and_each_flushed_row_including_null_values(tmp_path):
    output = tmp_path / "frames.csv"
    writer = CSVFrameResultWriter(output)
    session = RecognitionSessionFactory()
    writer.start(session)

    assert output.read_text(encoding="utf-8").splitlines() == [",".join(writer.FIELDNAMES)]
    assert writer.FIELDNAMES[:15] == (
        "capture_source", "source_reference", "camera_index", "expected_view",
        "camera_height_cm", "session_id", "athlete_id", "frame_index",
        "timestamp_seconds", "pose_detected", "pose_ready", "any_angle_valid",
        "left_knee_deg", "right_knee_deg", "left_hip_deg",
    )
    assert writer.FIELDNAMES[5:19] == (
        "session_id", "athlete_id", "frame_index", "timestamp_seconds",
        "pose_detected", "pose_ready", "any_angle_valid", "left_knee_deg",
        "right_knee_deg", "left_hip_deg", "right_hip_deg", "left_ankle_deg",
        "right_ankle_deg", "trunk_angle_deg",
    )
    assert len(writer.LANDMARK_FIELDNAMES) == len(PoseLandmarkName) * 3
    observed = PoseLandmark2DFactory(x=0.37, y=0.61, visibility=0.82)
    writer.write(
        BiomechanicalFrameResultFactory(
            session=session,
            frame_index=3,
            landmarks={PoseLandmarkName.LEFT_HIP: observed},
        )
    )
    rows = list(csv.DictReader(io.StringIO(output.read_text(encoding="utf-8"))))
    assert len(rows) == 1
    assert rows[0]["session_id"] == session.session_id
    assert [rows[0][field] for field in writer.CAPTURE_METADATA_FIELDNAMES] == [
        "", "", "", "", "",
    ]
    assert rows[0]["athlete_id"] == session.athlete_id
    assert rows[0]["frame_index"] == "3"
    assert rows[0]["pose_detected"] == "true"
    assert rows[0]["pose_ready"] == "false"
    assert rows[0]["any_angle_valid"] == "true"
    assert "pose_valid" not in rows[0]
    assert rows[0]["left_knee_deg"] == "90.0"
    assert rows[0]["right_knee_deg"] == ""
    assert rows[0]["left_hip_x"] == "0.37"
    assert rows[0]["left_hip_y"] == "0.61"
    assert rows[0]["left_hip_visibility"] == "0.82"
    assert rows[0]["right_hip_x"] == ""
    assert rows[0]["right_hip_y"] == ""
    assert rows[0]["right_hip_visibility"] == ""

    writer.write(
        BiomechanicalFrameResultFactory(
            session=session, frame_index=4, angles=BiomechanicalAngles(), pose_detected=False
        )
    )
    rows = list(csv.DictReader(io.StringIO(output.read_text(encoding="utf-8"))))
    assert len(rows) == 2
    assert rows[1]["pose_detected"] == "false"
    assert rows[1]["pose_ready"] == "false"
    assert rows[1]["any_angle_valid"] == "false"
    assert rows[1]["left_knee_deg"] == ""
    writer.stop()
    writer.stop()


def test_csv_writer_persists_fixed_capture_metadata_and_ignores_unknown_keys(tmp_path):
    output = tmp_path / "metadata.csv"
    metadata = {
        "capture_source": "video_file",
        "source_reference": "run.mp4",
        "camera_index": None,
        "expected_view": "lateral",
        "camera_height_cm": 103.5,
        "not_a_column": "ignored",
    }
    writer = CSVFrameResultWriter(output, capture_metadata=metadata)
    session = RecognitionSessionFactory()
    writer.start(session)
    writer.write(BiomechanicalFrameResultFactory(session=session))
    writer.stop()

    with output.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames) == writer.FIELDNAMES
        row = next(reader)
    assert [row[field] for field in writer.CAPTURE_METADATA_FIELDNAMES] == [
        "video_file", "run.mp4", "", "lateral", "103.5",
    ]
    assert "not_a_column" not in row


@pytest.mark.parametrize("metadata", [[], "live_camera", 12])
def test_csv_writer_rejects_non_mapping_capture_metadata(tmp_path, metadata):
    with pytest.raises(TypeError, match="capture_metadata must be a mapping or None"):
        CSVFrameResultWriter(tmp_path / "metadata.csv", capture_metadata=metadata)


def test_csv_writer_rejects_write_before_start_and_results_from_other_session(tmp_path):
    writer = CSVFrameResultWriter(tmp_path / "frames.csv")
    result = BiomechanicalFrameResultFactory()
    with pytest.raises(RuntimeError, match="not been started"):
        writer.write(result)

    writer.start(RecognitionSessionFactory())
    other_session_result = BiomechanicalFrameResultFactory(
        session=RecognitionSessionFactory(session_id="other")
    )
    with pytest.raises(ValueError, match="different recognition session"):
        writer.write(other_session_result)
    writer.stop()


def test_csv_writer_rejects_double_start(tmp_path):
    writer = CSVFrameResultWriter(tmp_path / "frames.csv")
    writer.start(RecognitionSessionFactory())
    with pytest.raises(RuntimeError, match="already started"):
        writer.start(RecognitionSessionFactory())
    writer.stop()


@pytest.mark.parametrize("key", [ord("q"), ord("s")])
def test_camera_cancel_or_stop_before_t_returns_no_frame_and_releases(monkeypatch, key):
    capture = FakeCapture([(True, object())])
    cv2 = _install_cv2(monkeypatch, capture, keys=[key])
    source = OpenCVCameraFrameSource(0)
    source.start(RecognitionSessionFactory())

    assert source.read_next() is None
    source.stop()
    assert capture.releases == 1
    assert cv2.destroyed == [source.window_name]


def test_camera_eof_and_open_failure_release_capture(monkeypatch):
    capture = FakeCapture([])
    cv2 = _install_cv2(monkeypatch, capture)
    source = OpenCVCameraFrameSource(0)
    source.start(RecognitionSessionFactory())
    assert source.read_next() is None
    assert capture.releases == 1
    assert cv2.destroyed == [source.window_name]

    closed_capture = FakeCapture(opened=False)
    _install_cv2(monkeypatch, closed_capture)
    with pytest.raises(RuntimeError, match="could not open camera"):
        OpenCVCameraFrameSource(0).start(RecognitionSessionFactory())
    assert closed_capture.releases == 1


@pytest.mark.parametrize("path", ["video.avi", "video.mkv"])
def test_video_adapter_rejects_unsupported_extensions(path):
    with pytest.raises(ValueError, match=".mp4 or .mov"):
        OpenCVVideoFileFrameSource(path)


def test_video_source_uses_fps_timestamps_and_releases_at_eof(tmp_path, monkeypatch):
    path = tmp_path / "run.MP4"
    path.touch()
    images = [object(), object()]
    capture = FakeCapture([(True, images[0]), (True, images[1])], fps=25.0)
    cv2 = _install_cv2(monkeypatch, capture)
    source = OpenCVVideoFileFrameSource(path)
    source.start(RecognitionSessionFactory())

    frame0 = source.read_next()
    frame1 = source.read_next()
    end = source.read_next()

    assert cv2.video_capture_calls == [(str(path),)]
    assert (frame0.frame_index, frame0.timestamp_seconds, frame0.payload) == (0, 0.0, images[0])
    assert frame1.frame_index == 1
    assert frame1.timestamp_seconds == pytest.approx(1 / 25.0)
    assert frame1.payload is images[1]
    assert end is None
    assert capture.releases == 1


@pytest.mark.parametrize("fps", [0, -1, float("nan")])
def test_video_source_uses_fallback_fps_when_metadata_is_invalid(tmp_path, monkeypatch, fps):
    path = tmp_path / "run.mov"
    path.touch()
    capture = FakeCapture([(True, object()), (True, object())], fps=fps)
    _install_cv2(monkeypatch, capture)
    source = OpenCVVideoFileFrameSource(path, fallback_fps=10)
    source.start(RecognitionSessionFactory())

    source.read_next()
    second = source.read_next()
    assert second.timestamp_seconds == pytest.approx(0.1)
    source.stop()
    assert capture.releases == 1


def test_video_source_missing_or_unreadable_file_fails_without_leaking_capture(tmp_path, monkeypatch):
    missing = OpenCVVideoFileFrameSource(tmp_path / "missing.mp4")
    with pytest.raises(ValueError, match="does not exist"):
        missing.start(RecognitionSessionFactory())

    path = tmp_path / "broken.mp4"
    path.touch()
    capture = FakeCapture(opened=False)
    _install_cv2(monkeypatch, capture)
    with pytest.raises(ValueError, match="could not open video"):
        OpenCVVideoFileFrameSource(path).start(RecognitionSessionFactory())
    assert capture.releases == 1


class FakeImage:
    shape = (100, 200, 3)

    def __init__(self, label="image"):
        self.label = label

    def copy(self):
        return FakeImage(self.label + "-overlay")


class FakeDetector:
    def __init__(self, pose_or_poses):
        self.poses = list(pose_or_poses) if isinstance(pose_or_poses, list) else None
        self.pose = pose_or_poses if self.poses is None else None
        self.images = []

    def detect_from_bgr(self, image):
        self.images.append(image)
        return self.poses.pop(0) if self.poses is not None else self.pose


class FakeRawWriter:
    def __init__(self):
        self.starts = []
        self.frames = []
        self.stops = 0

    def start(self, *, fps, frame_size):
        self.starts.append((fps, frame_size))

    def write(self, image):
        self.frames.append(image)

    def stop(self):
        self.stops += 1


class FakeVerificationCapture:
    def __init__(self, frames=(), opened=True):
        self.frames = list(frames)
        self.opened = opened
        self.releases = 0

    def isOpened(self):
        return self.opened

    def read(self):
        return (True, self.frames.pop(0)) if self.frames else (False, None)

    def release(self):
        self.releases += 1


def _ready_pose():
    return {
        PoseLandmarkName.LEFT_SHOULDER: PoseLandmark2D(0.3, 0.05, 1.0),
        PoseLandmarkName.LEFT_HIP: PoseLandmark2D(0.3, 0.2, 1.0),
        PoseLandmarkName.LEFT_KNEE: PoseLandmark2D(0.3, 0.5, 1.0),
        PoseLandmarkName.LEFT_ANKLE: PoseLandmark2D(0.6, 0.5, 1.0),
        PoseLandmarkName.LEFT_FOOT_INDEX: PoseLandmark2D(0.8, 0.5, 1.0),
    }


def test_camera_requires_ready_streak_and_stores_raw_video_only_after_t(monkeypatch):
    images = [FakeImage("frame-{}".format(i)) for i in range(7)]
    capture = FakeCapture([(True, image) for image in images])
    cv2 = _install_cv2(
        monkeypatch, capture,
        keys=[ord("t"), -1, -1, -1, ord("t"), -1, ord("s")],
    )
    ready = _ready_pose()
    detector = FakeDetector([None, ready, None, ready, ready, ready, ready])
    raw_writer = FakeRawWriter()
    source = OpenCVCameraFrameSource(
        2,
        pose_detector=detector,
        readiness_frames=2,
        raw_video_path="capture.mp4",
        raw_video_writer=raw_writer,
    )
    arrivals = iter([10.0, 10.05, 10.1, 10.15, 10.2, 10.25, 10.3])
    monkeypatch.setattr(
        "detection.infrastructure.camera_source.time.monotonic", lambda: next(arrivals)
    )
    source.start(RecognitionSessionFactory())

    captured = source.read_next()
    calls_before_analysis = list(detector.images)
    analyzed = MediaPipeBiomechanicalAnalyzer(detector).analyze(
        RecognitionSessionFactory(), captured
    )
    assert detector.images == calls_before_analysis
    captured_second = source.read_next()
    ended = source.read_next()

    assert captured.frame_index == 0
    assert captured.timestamp_seconds == 0.0
    assert isinstance(captured.payload, AnalyzedFramePayload)
    assert captured.payload.image is images[4]
    assert dict(captured.payload.landmarks) == ready
    assert analyzed.pose_ready is True
    assert captured_second.frame_index == 1
    assert captured_second.timestamp_seconds == pytest.approx(0.05)
    assert captured_second.payload.image is images[5]
    assert ended is None
    assert detector.images == images
    assert raw_writer.starts == [(pytest.approx(20.0), (200, 100))]
    assert raw_writer.frames == [images[4], images[5]]
    assert all(image.label.endswith("-overlay") for _, image in cv2.shown)
    assert any(call[0] == "line" for call in cv2.draw_calls)
    assert any(call[0] == "circle" for call in cv2.draw_calls)
    assert any("RECORDING" in call[2] for call in cv2.draw_calls if call[0] == "text")
    assert any("READY" in call[2] for call in cv2.draw_calls if call[0] == "text")
    assert capture.releases == 1
    assert raw_writer.stops == 1
    assert cv2.destroyed == [source.window_name]


def test_camera_falls_back_to_configured_fps_when_preview_sample_is_too_short(
    monkeypatch,
):
    image = FakeImage("first")
    capture = FakeCapture([(True, image)], fps=0)
    _install_cv2(monkeypatch, capture, keys=[ord("t")])
    raw_writer = FakeRawWriter()
    source = OpenCVCameraFrameSource(
        0,
        pose_detector=FakeDetector(_ready_pose()),
        readiness_frames=1,
        raw_video_path="capture.mp4",
        raw_video_writer=raw_writer,
        fallback_fps=15.0,
    )
    monkeypatch.setattr("detection.infrastructure.camera_source.time.monotonic", lambda: 4.0)
    source.start(RecognitionSessionFactory())

    frame = source.read_next()

    assert frame.timestamp_seconds == 0.0
    assert raw_writer.starts == [(15.0, (200, 100))]
    source.stop()


@pytest.mark.parametrize("key", [ord("q"), ord("s")])
def test_camera_cancel_or_stop_before_t_returns_no_frame_and_releases(monkeypatch, key):
    capture = FakeCapture([(True, FakeImage())])
    cv2 = _install_cv2(monkeypatch, capture, keys=[key])
    source = OpenCVCameraFrameSource(0, pose_detector=FakeDetector(None))
    source.start(RecognitionSessionFactory())

    assert source.read_next() is None
    source.stop()
    assert capture.releases == 1
    assert cv2.destroyed == [source.window_name]


def test_camera_eof_and_open_failure_release_capture(monkeypatch):
    capture = FakeCapture([])
    cv2 = _install_cv2(monkeypatch, capture)
    source = OpenCVCameraFrameSource(0, pose_detector=FakeDetector(None))
    source.start(RecognitionSessionFactory())
    assert source.read_next() is None
    assert capture.releases == 1
    assert cv2.destroyed == [source.window_name]

    closed_capture = FakeCapture(opened=False)
    _install_cv2(monkeypatch, closed_capture)
    with pytest.raises(RuntimeError, match="could not open camera"):
        OpenCVCameraFrameSource(0).start(RecognitionSessionFactory())
    assert closed_capture.releases == 1


def test_camera_detector_error_cleans_up_camera_window_and_raw_writer(monkeypatch):
    capture = FakeCapture([(True, FakeImage())])
    cv2 = _install_cv2(monkeypatch, capture)

    class BrokenDetector:
        def detect_from_bgr(self, _image):
            raise RuntimeError("detector failed")

        def close(self):
            self.closed = True

    raw_writer = FakeRawWriter()
    detector = BrokenDetector()
    source = OpenCVCameraFrameSource(
        0,
        pose_detector_factory=lambda: detector,
        raw_video_path="capture.mp4",
        raw_video_writer=raw_writer,
    )
    source.start(RecognitionSessionFactory())
    with pytest.raises(RuntimeError, match="detector failed"):
        source.read_next()
    assert capture.releases == 1
    assert raw_writer.stops == 1
    assert detector.closed is True
    assert cv2.destroyed == [source.window_name]


def test_raw_video_writer_reserves_destination_and_uses_fps_and_frame_size(tmp_path):
    path = tmp_path / "capture.mp4"

    class Encoder:
        def __init__(self, output_path):
            self.output_path = output_path
            self.frames = []
            self.releases = 0

        def isOpened(self):
            return True

        def write(self, image):
            self.frames.append(image)

        def release(self):
            self.releases += 1
            self.output_path.write_bytes(b"encoded mp4")

    encoder = Encoder(path)
    calls = []
    verification_capture = FakeVerificationCapture([object()])

    def make_encoder(*args):
        calls.append(args)
        return encoder

    verification_calls = []

    def make_verification_capture(output_path):
        verification_calls.append(output_path)
        return verification_capture

    writer = OpenCVRawVideoWriter(
        path,
        writer_factory=make_encoder,
        verification_capture_factory=make_verification_capture,
    )
    writer.start(fps=24.0, frame_size=(640, 480))
    raw_frame = FakeImage("raw")
    writer.write(raw_frame)
    writer.stop()

    assert calls == [(str(path), 24.0, (640, 480))]
    assert encoder.frames == [raw_frame]
    assert encoder.releases == 1
    assert path.exists()
    assert verification_calls == [str(path)]
    assert verification_capture.releases == 1


@pytest.mark.parametrize(
    ("capture_factory", "message"),
    [
        (lambda: FakeVerificationCapture(opened=False), "could not open raw video"),
        (lambda: FakeVerificationCapture(), "decoded no frames"),
        (
            lambda: FakeVerificationCapture([object(), object()]),
            "frame count mismatch",
        ),
    ],
    ids=["mp4-does-not-open", "zero-decoded-frames", "decoded-count-mismatch"],
)
def test_raw_video_writer_verification_failure_releases_writer_and_keeps_partial_mp4(
    tmp_path, capture_factory, message
):
    path = tmp_path / "partial.mp4"

    class Encoder:
        def __init__(self):
            self.releases = 0

        def isOpened(self):
            return True

        def write(self, _image):
            pass

        def release(self):
            self.releases += 1
            path.write_bytes(b"partial encoded mp4")

    encoder = Encoder()
    verification_capture = capture_factory()
    writer = OpenCVRawVideoWriter(
        path,
        writer_factory=lambda *_args: encoder,
        verification_capture_factory=lambda _path: verification_capture,
    )
    writer.start(fps=24.0, frame_size=(640, 480))
    writer.write(FakeImage("raw"))

    with pytest.raises(RuntimeError, match=message):
        writer.stop()

    assert encoder.releases == 1
    assert verification_capture.releases == 1
    assert path.read_bytes() == b"partial encoded mp4"


def test_raw_video_writer_stop_before_start_does_not_verify(tmp_path):
    path = tmp_path / "not-started.mp4"
    verification_calls = []
    writer = OpenCVRawVideoWriter(
        path,
        verification_capture_factory=lambda output_path: verification_calls.append(
            output_path
        ),
    )

    writer.stop()

    assert verification_calls == []
    assert not path.exists()


def test_raw_video_writer_accepts_matching_decoded_frame_count(tmp_path):
    path = tmp_path / "matching.mp4"

    class Encoder:
        def isOpened(self):
            return True

        def write(self, _image):
            pass

        def release(self):
            path.write_bytes(b"valid encoded mp4")

    verification_capture = FakeVerificationCapture([object(), object()])
    writer = OpenCVRawVideoWriter(
        path,
        writer_factory=lambda *_args: Encoder(),
        verification_capture_factory=lambda _path: verification_capture,
    )
    writer.start(fps=24.0, frame_size=(640, 480))
    writer.write(FakeImage("first"))
    writer.write(FakeImage("second"))

    writer.stop()

    assert path.read_bytes() == b"valid encoded mp4"
    assert verification_capture.releases == 1


def test_raw_video_writer_collision_never_overwrites_existing_output(tmp_path):
    path = tmp_path / "existing.mp4"
    path.write_bytes(b"do not replace")
    writer = OpenCVRawVideoWriter(path, writer_factory=lambda *_: pytest.fail("opened"))

    with pytest.raises(FileExistsError):
        writer.start(fps=30.0, frame_size=(200, 100))

    assert path.read_bytes() == b"do not replace"


def test_raw_video_writer_failed_open_releases_and_removes_its_reservation(tmp_path):
    path = tmp_path / "broken.mp4"

    class ClosedEncoder:
        def __init__(self):
            self.releases = 0

        def isOpened(self):
            return False

        def release(self):
            self.releases += 1

    encoder = ClosedEncoder()
    writer = OpenCVRawVideoWriter(path, writer_factory=lambda *_: encoder)
    with pytest.raises(RuntimeError, match="could not open raw video"):
        writer.start(fps=30.0, frame_size=(200, 100))

    assert encoder.releases == 1
    assert not path.exists()


def test_analyzer_adapter_maps_detector_landmarks_to_domain_result():
    image = FakeImage()
    pose = _ready_pose()
    detector = FakeDetector(pose)
    session = RecognitionSessionFactory()
    frame = type("Frame", (), {"payload": image, "frame_index": 4, "timestamp_seconds": 0.4})()

    result = MediaPipeBiomechanicalAnalyzer(detector).analyze(session, frame)

    assert detector.images == [image]
    assert result.session is session
    assert result.frame_index == 4
    assert result.timestamp_seconds == pytest.approx(0.4)
    assert result.angles.left_knee_deg == pytest.approx(90.0)
    assert result.pose_detected is True
    assert result.pose_ready is True
    assert result.landmarks[PoseLandmarkName.LEFT_HIP] == pose[PoseLandmarkName.LEFT_HIP]


def test_analyzer_uses_cached_preview_pose_without_a_second_detector_call():
    image = FakeImage("cached")
    pose = _ready_pose()
    detector = FakeDetector(None)
    payload = AnalyzedFramePayload(image, pose)
    frame = type(
        "Frame",
        (),
        {"payload": payload, "frame_index": 5, "timestamp_seconds": 0.5},
    )()

    result = MediaPipeBiomechanicalAnalyzer(detector).analyze(
        RecognitionSessionFactory(), frame
    )

    assert detector.images == []
    assert result.pose_detected is True
    assert result.pose_ready is True
    assert dict(result.landmarks) == pose


def test_analyzer_preserves_cached_negative_detection_without_rerunning_detector():
    detector = FakeDetector(_ready_pose())
    frame = type(
        "Frame",
        (),
        {
            "payload": AnalyzedFramePayload(FakeImage(), None),
            "frame_index": 6,
            "timestamp_seconds": 0.6,
        },
    )()

    result = MediaPipeBiomechanicalAnalyzer(detector).analyze(
        RecognitionSessionFactory(), frame
    )

    assert detector.images == []
    assert result.pose_detected is False
    assert result.pose_ready is False
    assert result.landmarks == {}


def test_analyzer_returns_unavailable_angles_when_detector_finds_no_pose():
    detector = FakeDetector(None)
    frame = type("Frame", (), {"payload": FakeImage(), "frame_index": 0, "timestamp_seconds": 0.0})()

    result = MediaPipeBiomechanicalAnalyzer(detector).analyze(
        RecognitionSessionFactory(), frame
    )

    assert all(value is None for value in result.angles.as_dict().values())
    assert result.pose_detected is False


@pytest.mark.parametrize("image", [object(), type("BadImage", (), {"shape": (100,)})()])
def test_analyzer_rejects_invalid_image_shape(image):
    frame = type("Frame", (), {"payload": image, "frame_index": 0, "timestamp_seconds": 0.0})()
    with pytest.raises(ValueError, match="height and width"):
        MediaPipeBiomechanicalAnalyzer(FakeDetector(None)).analyze(
            RecognitionSessionFactory(), frame
        )


def test_analyzer_rejects_detector_output_without_landmark_mapping():
    detector = FakeDetector(None)
    detector.pose = []
    frame = type("Frame", (), {"payload": FakeImage(), "frame_index": 0, "timestamp_seconds": 0.0})()
    with pytest.raises(TypeError, match="mapping or None"):
        MediaPipeBiomechanicalAnalyzer(detector).analyze(
            RecognitionSessionFactory(), frame
        )


class FakeMediaPipePoint:
    def __init__(self, x=0.0, y=0.0, visibility=1.0):
        self.x = x
        self.y = y
        self.visibility = visibility


class FakeMediaPipePose:
    def __init__(self, pose_landmarks):
        self.landmark = pose_landmarks


class FakeMediaPipePoseModel:
    def __init__(self, results):
        self.results = results
        self.processed_images = []
        self.close_calls = 0

    def process(self, image):
        self.processed_images.append(image)
        return self.results

    def close(self):
        self.close_calls += 1


def _install_mediapipe(monkeypatch, results):
    model = FakeMediaPipePoseModel(results)

    def create_pose(**options):
        model.options = options
        return model

    pose_api = types.SimpleNamespace(Pose=create_pose)
    module = types.ModuleType("mediapipe")
    module.solutions = types.SimpleNamespace(pose=pose_api)
    monkeypatch.setitem(sys.modules, "mediapipe", module)
    return model


def test_pose_detector_converts_bgr_and_maps_model_indices_to_anatomical_names(monkeypatch):
    points = [FakeMediaPipePoint() for _ in range(33)]
    points[11] = FakeMediaPipePoint(0.1, 0.2, 0.91)
    points[23] = FakeMediaPipePoint(0.3, 0.4, 0.82)
    points[25] = FakeMediaPipePoint(0.5, 0.6, 0.73)
    image = FakeImage()
    model = _install_mediapipe(
        monkeypatch, types.SimpleNamespace(pose_landmarks=FakeMediaPipePose(points))
    )
    cv2 = _install_cv2(monkeypatch, FakeCapture())

    detector = MediaPipePoseDetector(
        model_complexity=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.7,
    )
    landmarks = detector.detect_from_bgr(image)

    assert model.options == {
        "static_image_mode": False,
        "model_complexity": 1,
        "smooth_landmarks": True,
        "min_detection_confidence": 0.6,
        "min_tracking_confidence": 0.7,
    }
    converted = ("rgb", image)
    assert cv2.color_conversions == [(image, cv2.COLOR_BGR2RGB, converted)]
    assert model.processed_images == [converted]
    assert landmarks[PoseLandmarkName.LEFT_SHOULDER] == PoseLandmark2DFactory(
        x=0.1, y=0.2, visibility=0.91
    )
    assert landmarks[PoseLandmarkName.LEFT_HIP] == PoseLandmark2DFactory(
        x=0.3, y=0.4, visibility=0.82
    )
    assert landmarks[PoseLandmarkName.LEFT_KNEE] == PoseLandmark2DFactory(
        x=0.5, y=0.6, visibility=0.73
    )
    assert len(landmarks) == len(PoseLandmarkName)
    detector.close()
    detector.close()
    assert model.close_calls == 1


def test_pose_detector_returns_none_when_mediapipe_finds_no_pose(monkeypatch):
    _install_mediapipe(monkeypatch, types.SimpleNamespace(pose_landmarks=None))
    _install_cv2(monkeypatch, FakeCapture())

    detector = MediaPipePoseDetector()

    assert detector.detect_from_bgr(FakeImage()) is None


def test_pose_detector_rejects_detection_after_close(monkeypatch):
    model = _install_mediapipe(monkeypatch, types.SimpleNamespace(pose_landmarks=None))
    _install_cv2(monkeypatch, FakeCapture())
    detector = MediaPipePoseDetector()
    detector.close()

    with pytest.raises(RuntimeError, match="closed"):
        detector.detect_from_bgr(FakeImage())
    assert model.close_calls == 1

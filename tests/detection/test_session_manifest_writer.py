"""Unit tests for exclusive and atomic session-manifest persistence."""

import json

import pytest

from detection.infrastructure.session_manifest_writer import SessionManifestWriter


def _start(writer):
    writer.start(
        session_id="session-1",
        athlete_id="runner-1",
        output_csv="angles.csv",
        raw_mp4="capture.mp4",
        source_reference="source.mov",
        capture_metadata={"capture_source": "live_camera"},
    )


@pytest.mark.parametrize(
    ("status", "counts", "error"),
    [
        (
            "complete",
            {
                "frames_written": 4,
                "pose_detected": 3,
                "pose_ready": 2,
                "raw_video_frames_written": 7,
            },
            None,
        ),
        (
            "empty",
            {
                "frames_written": 0,
                "pose_detected": 0,
                "pose_ready": 0,
                "raw_video_frames_written": 0,
            },
            None,
        ),
        (
            "failed",
            {
                "frames_written": 2,
                "pose_detected": 1,
                "pose_ready": 1,
                "raw_video_frames_written": 5,
            },
            ValueError("frame read failed"),
        ),
    ],
)
def test_manifest_records_each_final_status_counts_and_error(tmp_path, status, counts, error):
    path = tmp_path / "session.manifest.json"
    writer = SessionManifestWriter(path)
    _start(writer)

    initial = json.loads(path.read_text(encoding="utf-8"))
    assert initial["status"] == "in_progress"
    assert initial["finished_at_utc"] is None
    assert initial["frames_written"] == 0

    if status == "complete":
        writer.complete(**counts)
    elif status == "empty":
        writer.empty(**counts)
    else:
        writer.fail(error, **counts)

    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["status"] == status
    assert manifest["session_id"] == "session-1"
    assert manifest["athlete_id"] == "runner-1"
    assert manifest["output_csv"] == "angles.csv"
    assert manifest["raw_mp4"] == "capture.mp4"
    assert manifest["source_reference"] == "source.mov"
    assert manifest["capture_metadata"] == {"capture_source": "live_camera"}
    assert manifest["started_at_utc"].endswith("Z")
    assert manifest["finished_at_utc"].endswith("Z")
    assert {name: manifest[name] for name in counts} == counts
    assert manifest["error_type"] == (type(error).__name__ if error else None)
    assert manifest["error_message"] == (str(error) if error else None)


def test_start_is_exclusive_and_preserves_the_existing_manifest(tmp_path):
    path = tmp_path / "occupied.json"
    original = '{"owner": "another session"}\n'
    path.write_text(original, encoding="utf-8")
    writer = SessionManifestWriter(path)

    with pytest.raises(FileExistsError):
        _start(writer)

    assert path.read_text(encoding="utf-8") == original
    assert list(tmp_path.iterdir()) == [path]


def test_final_record_replaces_atomically_and_is_always_valid_json(tmp_path, monkeypatch):
    path = tmp_path / "atomic.manifest.json"
    writer = SessionManifestWriter(path)
    _start(writer)
    real_replace = __import__("os").replace
    observed = []

    def inspect_then_replace(temporary, destination):
        assert destination == str(path)
        observed.append(json.loads(path.read_text(encoding="utf-8")))
        observed.append(json.loads(open(temporary, encoding="utf-8").read()))
        real_replace(temporary, destination)

    monkeypatch.setattr("detection.infrastructure.session_manifest_writer.os.replace", inspect_then_replace)
    writer.complete(
        frames_written=1,
        pose_detected=1,
        pose_ready=1,
        raw_video_frames_written=1,
    )

    assert [record["status"] for record in observed] == ["in_progress", "complete"]
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "complete"
    assert list(tmp_path.iterdir()) == [path]


def test_finalization_rejects_invalid_counts_without_finishing_session(tmp_path):
    path = tmp_path / "counts.manifest.json"
    writer = SessionManifestWriter(path)
    _start(writer)

    with pytest.raises(ValueError, match="pose_ready <= pose_detected <= frames_written"):
        writer.complete(
            frames_written=1,
            pose_detected=0,
            pose_ready=1,
        )

    writer.fail(RuntimeError("write failed"), frames_written=1, pose_detected=0)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["frames_written"] == 1

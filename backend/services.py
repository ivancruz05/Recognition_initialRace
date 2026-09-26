"""Adapters that translate HTTP requests into `detection` calls.

Nothing in this file does analysis. It owns file handling, calibration
resolution and entity -> schema conversion so the routes stay declarative.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import cv2

from detection.entities import AnalysisReport
from detection.interfaces import PoseDetectorInterface
from detection.pipeline import DroneAnalysisConfig, DroneAnalysisReport, DroneAnalyzer
from detection.vision.calibration import ArUcoCalibration
from detection.vision.tracker import AthleteTracker

from backend import schemas


class AnalysisError(RuntimeError):
    """Raised when a request cannot be turned into a valid analysis."""


@contextmanager
def _staged(data: Optional[bytes], suffix: str, prefix: str) -> Iterator[Optional[Path]]:
    """Write bytes to a temp file, or yield None when nothing was sent.

    The file is removed on exit, so callers must finish their work inside.
    """
    if not data:
        yield None
        return

    tmp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    target = tmp_dir / f"upload{suffix}"
    try:
        target.write_bytes(data)
        yield target
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _suffix(filename: Optional[str], default: str = ".mp4") -> str:
    if not filename or "." not in filename:
        return default
    return filename[filename.rfind(".") :]


def _probe_frame_shape(video_path: Path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    shape = (
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
    )
    cap.release()
    return shape


def _load_calibration_file(calibration_json: bytes) -> ArUcoCalibration:
    try:
        json.loads(calibration_json.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"Calibration file is not valid JSON: {exc}") from exc

    with _staged(calibration_json, ".json", "drone-cal-") as staged:
        try:
            return ArUcoCalibration.load(staged)
        except Exception as exc:
            raise AnalysisError(f"Calibration file is not usable: {exc}") from exc


def analyze_upload(
    video_bytes: bytes,
    video_filename: Optional[str],
    calibration_json: Optional[bytes] = None,
    pixels_per_meter: Optional[float] = None,
    *,
    config: Optional[DroneAnalysisConfig] = None,
    pose_detector: Optional[PoseDetectorInterface] = None,
    tracker: Optional[AthleteTracker] = None,
) -> schemas.AnalyzeResponse:
    """Run the drone pipeline over one uploaded video.

    The video is staged to disk once and reused for both frame-size probing and
    analysis, so a large upload is not written twice.
    """
    if not video_bytes:
        raise AnalysisError("No video was uploaded")

    with _staged(video_bytes, _suffix(video_filename), "drone-video-") as staged:
        if staged is None:
            raise AnalysisError("No video was uploaded")

        if calibration_json:
            calibration = _load_calibration_file(calibration_json)
        elif pixels_per_meter:
            frame_shape = _probe_frame_shape(staged)
            if frame_shape is None:
                raise AnalysisError(
                    "Could not read the video to derive its frame size; "
                    "provide a calibration file instead"
                )
            calibration = ArUcoCalibration.from_scale(pixels_per_meter, frame_shape)
        else:
            raise AnalysisError("Provide either a calibration file or pixels_per_meter")

        analyzer = DroneAnalyzer(
            calibration=calibration,
            config=config or DroneAnalysisConfig(),
            pose_detector=pose_detector,
            tracker=tracker,
        )
        try:
            report = analyzer.analyze_video(str(staged))
        finally:
            analyzer.close()

    return to_analyze_response(report)


def measure_upload(
    video_bytes: bytes,
    video_filename: Optional[str],
    *,
    known_height_cm: Optional[float] = None,
    sample_frames: int = 30,
    pose_detector: Optional[PoseDetectorInterface] = None,
) -> schemas.AnalyzeReportResponse:
    """Measure body dimensions from an uploaded video.

    Uses the same frame-sampling and pose-validation gate as the CLI, so both
    entry points reject the same frames.
    """
    from detection.pipelines import MeasurementPipeline

    if not video_bytes:
        raise AnalysisError("No video was uploaded")

    with _staged(video_bytes, _suffix(video_filename), "drone-video-") as staged:
        if staged is None:
            raise AnalysisError("No video was uploaded")

        video_name = staged.name
        pipeline = MeasurementPipeline(pose_detector=pose_detector)
        try:
            result = pipeline.measure_video(
                str(staged),
                known_height_cm=known_height_cm,
                sample_frames=sample_frames,
            )
        finally:
            pipeline.close()

    summary = result.get("validation_summary", {})
    m = result["measurements"]

    return schemas.AnalyzeReportResponse(
        athlete_name="Unknown",
        video_path=video_name,
        frames_analyzed=int(summary.get("total_valid", 0)),
        measurements=schemas.BodyMeasurementsResponse(
            height_cm=m.height_cm,
            leg_length_cm=m.leg_length_cm,
            arm_length_cm=m.arm_length_cm,
            torso_length_cm=m.torso_length_cm,
            foot_length_cm=m.foot_length_cm,
            shoulder_width_cm=m.shoulder_width_cm,
            confidence=m.confidence,
        ),
        recommendations=[],
    )


def to_analyze_response(report: DroneAnalysisReport) -> schemas.AnalyzeResponse:
    """Convert a pipeline report into the API response shape."""
    kinematics = None
    if report.kinematics is not None:
        kinematics = schemas.KinematicsSummary(
            max_velocity_ms=report.kinematics.max_velocity_ms,
            average_velocity_ms=report.kinematics.average_velocity_ms,
            total_distance_m=report.kinematics.total_distance_m,
        )

    return schemas.AnalyzeResponse(
        video_path=Path(report.video_path).name,
        fps=report.fps,
        frames_processed=report.frames_processed,
        calibration_valid=report.calibration_valid,
        posture_score=report.posture_score,
        trunk_angle_deg=report.trunk_angle_deg,
        variables=dict(report.variables),
        kinematics=kinematics,
    )


def to_report_response(report: AnalysisReport) -> schemas.AnalyzeReportResponse:
    """Convert a body-measurement report into the API response shape."""
    m = report.measurements
    return schemas.AnalyzeReportResponse(
        athlete_name=report.athlete_name,
        video_path=Path(report.video_path).name,
        frames_analyzed=report.frames_analyzed,
        measurements=schemas.BodyMeasurementsResponse(
            height_cm=m.height_cm,
            leg_length_cm=m.leg_length_cm,
            arm_length_cm=m.arm_length_cm,
            torso_length_cm=m.torso_length_cm,
            foot_length_cm=m.foot_length_cm,
            shoulder_width_cm=m.shoulder_width_cm,
            confidence=m.confidence,
        ),
        recommendations=list(report.comparison.recommendations),
    )

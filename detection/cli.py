"""CLI commands for the detection module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import cv2

from detection.metrics.validation import ValidationAnalyzer
from detection.pipeline import DroneAnalysisConfig, DroneAnalyzer
from detection.vision.calibration import ArUcoCalibration, default_track_marker_config


def _resolve_calibration(
    calibration: Optional[str],
    pixels_per_meter: Optional[float],
    video_path: str,
) -> Optional[ArUcoCalibration]:
    """Build a calibration from a JSON file, a raw px/m scale, or nothing."""
    if calibration:
        return ArUcoCalibration.load(calibration)

    if pixels_per_meter:
        cap = cv2.VideoCapture(video_path)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()
        return ArUcoCalibration.from_scale(pixels_per_meter, (height, width))

    return None


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--calibration", "-c", type=click.Path(exists=True), help="Calibration JSON file")
@click.option("--pixels-per-meter", type=float, default=None, help="Fallback scale if no calibration file")
@click.option("--output", "-o", type=click.Path(), default="analysis_output", help="Output directory")
@click.option("--stabilize", is_flag=True, help="Apply video stabilisation")
@click.option("--annotate", is_flag=True, help="Generate annotated output video")
@click.option("--yolo-model", default="yolov8n.pt", help="YOLO model name/path")
@click.option("--tracker", default="bytetrack.yaml", help="Ultralytics tracker config")
@click.option("--sample-interval", type=int, default=1, help="Process every N frames")
@click.option("--max-frames", type=int, default=None, help="Limit number of frames to process")
@click.option("--start-region", type=str, default=None, help="Start ROI as JSON [x1,y1,x2,y2]")
def analyze(
    video_path: str,
    calibration: Optional[str],
    pixels_per_meter: Optional[float],
    output: str,
    stabilize: bool,
    annotate: bool,
    yolo_model: str,
    tracker: str,
    sample_interval: int,
    max_frames: Optional[int],
    start_region: Optional[str],
):
    """Analyze a drone video: tracking + pose + calibration -> biomechanics."""
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    cal = _resolve_calibration(calibration, pixels_per_meter, video_path)
    if cal is None:
        click.echo("Error: provide --calibration or --pixels-per-meter")
        return

    start_bbox = None
    if start_region:
        try:
            start_bbox = tuple(json.loads(start_region))
        except json.JSONDecodeError:
            click.echo("Error: --start-region must be a JSON array [x1,y1,x2,y2]")
            return

    config = DroneAnalysisConfig(
        use_stabilization=stabilize,
        yolo_model=yolo_model,
        tracker=tracker,
        sample_interval=sample_interval,
        max_frames=max_frames,
        start_region=start_bbox,
    )

    analyzer = DroneAnalyzer(calibration=cal, config=config)
    try:
        output_video = str(output_dir / "annotated.mp4") if annotate else None
        report = analyzer.analyze_video(video_path, output_video_path=output_video)
    finally:
        analyzer.close()

    analyzer.save_report(report, output_dir / "results.json")

    click.echo(f"\nProcessed {report.frames_processed} frames")
    click.echo(f"Calibration valid: {report.calibration_valid}")
    click.echo("\nVariables:")
    for var, value in report.variables.items():
        click.echo(f"  {var}: {value:.3f}")

    if report.kinematics:
        click.echo(f"\nMax velocity: {report.kinematics.max_velocity_ms:.2f} m/s")
        click.echo(f"Average velocity: {report.kinematics.average_velocity_ms:.2f} m/s")
        click.echo(f"Total distance: {report.kinematics.total_distance_m:.2f} m")

    click.echo(f"\nReport saved to {output_dir / 'results.json'}")
    if annotate:
        click.echo(f"Annotated video saved to {output_video}")


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--calibration", "-c", type=click.Path(exists=True), help="Calibration JSON file")
@click.option("--pixels-per-meter", type=float, default=None, help="Fallback scale if no calibration file")
@click.option("--output", "-o", type=click.Path(), default="annotated.mp4", help="Output video path")
@click.option("--stabilize", is_flag=True, help="Apply video stabilisation")
@click.option("--yolo-model", default="yolov8n.pt", help="YOLO model name/path")
@click.option("--tracker", default="bytetrack.yaml", help="Ultralytics tracker config")
@click.option("--sample-interval", type=int, default=1, help="Process every N frames")
@click.option("--max-frames", type=int, default=None, help="Limit number of frames to process")
def annotate(
    video_path: str,
    calibration: Optional[str],
    pixels_per_meter: Optional[float],
    output: str,
    stabilize: bool,
    yolo_model: str,
    tracker: str,
    sample_interval: int,
    max_frames: Optional[int],
):
    """Generate an annotated video with tracking boxes and pose landmarks."""
    cal = _resolve_calibration(calibration, pixels_per_meter, video_path)
    if cal is None:
        click.echo("Error: provide --calibration or --pixels-per-meter")
        return

    config = DroneAnalysisConfig(
        use_stabilization=stabilize,
        yolo_model=yolo_model,
        tracker=tracker,
        sample_interval=sample_interval,
        max_frames=max_frames,
    )

    analyzer = DroneAnalyzer(calibration=cal, config=config)
    try:
        analyzer.analyze_video(video_path, output_video_path=output)
    finally:
        analyzer.close()

    click.echo(f"Annotated video saved to {output}")


@click.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="calibration.json", help="Output calibration file")
@click.option("--marker-size", type=float, default=ArUcoCalibration.DEFAULT_MARKER_SIZE_M, help="Marker side in meters")
@click.option("--lane-width", type=float, default=1.22, help="Track lane width in meters")
@click.option("--distance", type=float, default=10.0, help="Sprint distance in meters")
@click.option("--pixels-per-meter", type=float, default=None, help="Fallback scale when markers are not present")
def calibrate(
    source: str,
    output: str,
    marker_size: float,
    lane_width: float,
    distance: float,
    pixels_per_meter: Optional[float],
):
    """Generate a px->m calibration from a reference image/video frame.

    SOURCE can be an image or video. If it is a video, the first frame is used.
    """
    image = _load_first_frame(source)
    if image is None:
        click.echo("Error: could not read source image/frame")
        return

    if pixels_per_meter is not None:
        cal = ArUcoCalibration.from_scale(pixels_per_meter, image.shape[:2])
        click.echo(f"Calibration created from scale: {pixels_per_meter:.2f} px/m")
    else:
        marker_config = default_track_marker_config(lane_width, distance)
        cal = ArUcoCalibration(
            marker_config=marker_config,
            marker_size_m=marker_size,
        )
        success = cal.calibrate_from_image(image)
        if not success:
            click.echo("Error: could not detect enough ArUco markers (need >= 4)")
            click.echo("Use --pixels-per-meter to create a fallback calibration")
            return
        click.echo(f"Calibration successful with {len(marker_config)} markers")

    cal.save(output)
    click.echo(f"Saved calibration to {output}")


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="ground_truth.json", help="Output template file")
@click.option("--athlete-id", type=str, default="P00", help="Athlete/session identifier")
@click.option("--frames", type=int, default=0, help="Number of frames to include; 0 = all")
def groundtruth(video_path: str, output: str, athlete_id: str, frames: int):
    """Generate a ground-truth JSON template for manual annotation.

    The template contains the four variables required by the project document
    (postura, velocidad, longitud_zancada, cadencia) and should be filled by
    a human annotator frame by frame or per session.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        click.echo("Error: could not open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    step = 1
    if frames > 0 and frames < total_frames:
        step = max(1, total_frames // frames)

    frame_entries = []
    for idx in range(0, total_frames, step):
        frame_entries.append({
            "frame_index": idx,
            "time_s": round(idx / fps, 3),
            "postura": None,
            "velocidad": None,
            "longitud_zancada": None,
            "cadencia": None,
        })

    payload = {
        "athlete_id": athlete_id,
        "video_path": video_path,
        "fps": fps,
        "total_frames": total_frames,
        "variables": ["postura", "velocidad", "longitud_zancada", "cadencia"],
        "unit": {
            "postura": "score 0-100 or degrees",
            "velocidad": "m/s",
            "longitud_zancada": "m",
            "cadencia": "steps/s",
        },
        "frames": frame_entries,
    }

    Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    click.echo(f"Ground-truth template saved to {output} ({len(frame_entries)} frames)")


@click.command()
@click.argument("results", type=click.Path(exists=True))
@click.argument("ground_truth", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output JSON report file")
@click.option("--athlete-id", type=str, default=None, help="Athlete/session identifier")
def validate(results: str, ground_truth: str, output: Optional[str], athlete_id: Optional[str]):
    """Validate automatic RESULTS against manual GROUND_TRUTH."""
    auto = json.loads(Path(results).read_text(encoding="utf-8"))
    gt = json.loads(Path(ground_truth).read_text(encoding="utf-8"))

    automatic_variables = auto.get("variables", {})
    manual_variables = _average_ground_truth(gt)

    aid = athlete_id or gt.get("athlete_id", "unknown")
    analyzer = ValidationAnalyzer()
    report = analyzer.compare(automatic_variables, manual_variables, athlete_id=aid)

    report_dict = ValidationAnalyzer.report_to_dict(report)
    click.echo(json.dumps(report_dict, indent=2))

    if output:
        Path(output).write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
        click.echo(f"\nValidation report saved to {output}")


def _load_first_frame(source: str):
    import numpy as np

    path = Path(source)
    if path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
        cap = cv2.VideoCapture(str(source))
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None
    return cv2.imread(str(source))


def _average_ground_truth(gt: Dict) -> Dict[str, float]:
    """Average non-null values per variable across all annotated frames."""
    frames: List[Dict] = gt.get("frames", [])
    averaged: Dict[str, float] = {}
    for var in gt.get("variables", []):
        values = [f[var] for f in frames if f.get(var) is not None]
        if values:
            averaged[var] = sum(values) / len(values)
    return averaged


def register(cli: click.Group) -> None:
    """Attach the detection commands to the root CLI group."""
    cli.add_command(calibrate)
    cli.add_command(analyze)
    cli.add_command(annotate)
    cli.add_command(groundtruth)
    cli.add_command(validate)

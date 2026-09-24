"""Analyze command - full drone video analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from drone_analysis.application.drone_pipeline import DroneAnalysisConfig, DroneAnalyzer
from drone_analysis.infrastructure.calibration.aruco import ArUcoCalibration


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
@click.option("--start-region", type=str, default=None, help='Start ROI as JSON [x1,y1,x2,y2]')
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

    if calibration:
        cal = ArUcoCalibration.load(calibration)
    elif pixels_per_meter:
        import cv2
        cap = cv2.VideoCapture(video_path)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cap.release()
        cal = ArUcoCalibration.from_scale(pixels_per_meter, (h, w))
    else:
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

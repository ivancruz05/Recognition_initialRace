"""Annotate command - generate an annotated video without full analysis report."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from drone_analysis.application.drone_pipeline import DroneAnalysisConfig, DroneAnalyzer
from drone_analysis.infrastructure.calibration.aruco import ArUcoCalibration


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

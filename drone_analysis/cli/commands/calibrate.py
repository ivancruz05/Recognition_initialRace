"""Calibrate command - create px->m calibration for a drone video."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
import cv2

from drone_analysis.infrastructure.calibration.aruco import (
    ArUcoCalibration,
    default_track_marker_config,
)


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
    path = Path(source)
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


def _load_first_frame(source: str) -> Optional["np.ndarray"]:
    import numpy as np
    path = Path(source)
    if path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"}:
        cap = cv2.VideoCapture(str(source))
        ret, frame = cap.read()
        cap.release()
        return frame if ret else None
    return cv2.imread(str(source))

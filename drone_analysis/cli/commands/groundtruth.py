"""Ground-truth command - generate a manual annotation template."""

from __future__ import annotations

import json
from pathlib import Path

import click
import cv2


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
            "postura": None,  # e.g. trunk angle in degrees or posture score 0-100
            "velocidad": None,  # m/s
            "longitud_zancada": None,  # m
            "cadencia": None,  # steps/s
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

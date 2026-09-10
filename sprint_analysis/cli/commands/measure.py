"""Measure command - Body measurements from video."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from sprint_analysis.application.pipelines import MeasurementPipeline
from sprint_analysis.domain.models import BodyMeasurements


def format_measurements(m: BodyMeasurements) -> str:
    """Format measurements for display."""
    lines = [
        "📏 MEDICIONES CORPORALES (LiDAR)",
        "-" * 40,
        f"  Estatura:          {m.height_cm:.1f} cm",
        f"  Longitud pierna:   {m.leg_length_cm:.1f} cm",
        f"  Longitud brazo:    {m.arm_length_cm:.1f} cm",
        f"  Longitud torso:    {m.torso_length_cm:.1f} cm",
        f"  Tamaño pie:        {m.foot_length_cm:.1f} cm",
        f"  Ancho hombros:     {m.shoulder_width_cm:.1f} cm",
        f"  Confianza:         {m.confidence:.0%}",
        f"  Depth válido:      {m.depth_valid_ratio:.1%}",
        "-" * 40,
    ]
    return "\n".join(lines)


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--height", type=float, help="Known height in cm")
@click.option("--output", "-o", type=click.Path(), help="Output JSON file")
def measure(video_path: str, height: Optional[float], output: Optional[str]):
    """Measure body dimensions from a video file."""
    pipeline = MeasurementPipeline()

    measurements = pipeline.measure_video(video_path, known_height_cm=height)

    click.echo(f"\n📹 Video: {video_path}\n")
    click.echo(format_measurements(measurements))

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "video": video_path,
            "known_height_cm": height,
            "measurements": {
                "height_cm": measurements.height_cm,
                "leg_length_cm": measurements.leg_length_cm,
                "arm_length_cm": measurements.arm_length_cm,
                "torso_length_cm": measurements.torso_length_cm,
                "foot_length_cm": measurements.foot_length_cm,
                "shoulder_width_cm": measurements.shoulder_width_cm,
            },
            "confidence": measurements.confidence,
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        click.echo(f"\n💾 Guardado en: {output}")

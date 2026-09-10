"""Analyze command - Full sprint analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from sprint_analysis.application.services import AnalysisService


@click.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--athlete", type=str, help='Athlete info as JSON: \'{"name":"Ivan","height_cm":179}\'')
@click.option("--output", "-o", type=click.Path(), help="Output directory")
@click.option("--frames", type=int, default=30, help="Number of frames to analyze")
def analyze(video_path: str, athlete: Optional[str], output: Optional[str], frames: int):
    """Analyze sprint start position from a video."""
    athlete_info = {}
    if athlete:
        try:
            athlete_info = json.loads(athlete)
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON for --athlete")
            return

    service = AnalysisService()
    report = service.analyze_video(video_path, athlete_info, sample_frames=frames)

    click.echo(f"\n{'='*50}")
    click.echo(f"  ANÁLISIS DE SPRINT")
    click.echo(f"{'='*50}\n")

    click.echo(f"📹 Video: {video_path}")
    click.echo(f"👤 Atleta: {report.athlete_name}")
    click.echo(f"📊 Frames analizados: {report.frames_analyzed}\n")

    click.echo("📏 MEDICIONES:")
    m = report.measurements
    click.echo(f"  Estatura:    {m.height_cm:.1f} cm")
    click.echo(f"  Pierna:      {m.leg_length_cm:.1f} cm")
    click.echo(f"  Brazo:       {m.arm_length_cm:.1f} cm")
    click.echo(f"  Torso:       {m.torso_length_cm:.1f} cm")
    click.echo(f"  Pie:         {m.foot_length_cm:.1f} cm")
    click.echo(f"  Hombros:     {m.shoulder_width_cm:.1f} cm\n")

    click.echo("📐 ÁNGULOS:")
    a = report.metrics.angles
    click.echo(f"  Rodilla izq: {a.left_knee:.1f}°")
    click.echo(f"  Rodilla der: {a.right_knee:.1f}°")
    click.echo(f"  Cadera izq:  {a.left_hip:.1f}°")
    click.echo(f"  Cadera der:  {a.right_hip:.1f}°")
    click.echo(f"  Tronco:      {a.trunk_angle:.1f}°\n")

    click.echo(f"⭐ CALIDAD: {report.metrics.quality_score:.0f}/100\n")

    click.echo("💡 RECOMENDACIONES:")
    for rec in report.comparison.recommendations:
        click.echo(f"  • {rec}")

    if output:
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

        report_data = {
            "video": video_path,
            "athlete": report.athlete_name,
            "frames_analyzed": report.frames_analyzed,
            "measurements": {
                "height_cm": m.height_cm,
                "leg_length_cm": m.leg_length_cm,
                "arm_length_cm": m.arm_length_cm,
                "torso_length_cm": m.torso_length_cm,
                "foot_length_cm": m.foot_length_cm,
                "shoulder_width_cm": m.shoulder_width_cm,
            },
            "angles": {
                "left_knee": a.left_knee,
                "right_knee": a.right_knee,
                "left_hip": a.left_hip,
                "right_hip": a.right_hip,
                "trunk": a.trunk_angle,
            },
            "quality_score": report.metrics.quality_score,
            "recommendations": report.comparison.recommendations,
        }

        with open(output_dir / "results.json", "w") as f:
            json.dump(report_data, f, indent=2)

        click.echo(f"\n💾 Guardado en: {output_dir}")

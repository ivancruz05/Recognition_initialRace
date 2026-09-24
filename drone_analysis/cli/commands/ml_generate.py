"""Generate a reproducible synthetic machine-learning dataset."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from drone_analysis.ml.synthetic import SyntheticDatasetConfig, SyntheticDatasetGenerator


@click.command("ml-generate")
@click.option("--output", "-o", type=click.Path(), default="data/synthetic_ml", help="Dataset output directory")
@click.option("--athletes", type=int, default=200, help="Number of synthetic athletes")
@click.option("--min-trials", type=int, default=3, help="Minimum trials per athlete")
@click.option("--max-trials", type=int, default=5, help="Maximum trials per athlete")
@click.option("--fps", type=int, default=30, help="Frames per second used for frame features")
@click.option("--seed", type=int, default=2026, help="Random seed")
@click.option("--noise", type=float, default=0.15, help="Measurement noise level from 0 to 1")
@click.option("--outlier-rate", type=float, default=0.05, help="Fraction of trials marked as outliers")
@click.option("--max-frames", type=int, default=None, help="Optional maximum frames per trial")
def ml_generate(
    output: str,
    athletes: int,
    min_trials: int,
    max_trials: int,
    fps: int,
    seed: int,
    noise: float,
    outlier_rate: float,
    max_frames: Optional[int],
):
    """Generate athletes.csv, trials.csv, frame_features.csv and splits.csv."""
    config = SyntheticDatasetConfig(
        n_athletes=athletes,
        min_trials=min_trials,
        max_trials=max_trials,
        fps=fps,
        seed=seed,
        noise_level=noise,
        outlier_rate=outlier_rate,
        max_frames_per_trial=max_frames,
    )
    summary = SyntheticDatasetGenerator(config).generate(output)
    click.echo(f"Dataset generated at {summary.output_dir}")
    click.echo(f"Athletes: {summary.athletes}")
    click.echo(f"Trials: {summary.trials}")
    click.echo(f"Frames: {summary.frames}")
    click.echo(f"Splits: {summary.split_counts}")
    click.echo(f"Trials CSV: {summary.files['trials']}")
    click.echo(f"Frame CSV: {summary.files['frames']}")
    click.echo(f"Metadata: {summary.files['metadata']}")

"""Train a baseline machine-learning model on synthetic sprint trials."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from drone_analysis.ml.trainer import train_baseline


@click.command("ml-train")
@click.argument("trials_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default="models/sprint_baseline", help="Model output directory")
@click.option("--trees", type=int, default=200, help="Number of trees in each Random Forest")
@click.option("--seed", type=int, default=42, help="Model random seed")
@click.option("--include-outliers", is_flag=True, help="Include synthetic high-noise trials")
def ml_train(
    trials_path: str,
    output: str,
    trees: int,
    seed: int,
    include_outliers: bool,
):
    """Train regression and classification baselines from trials.csv."""
    metrics = train_baseline(
        trials_path=trials_path,
        output_dir=output,
        n_estimators=trees,
        seed=seed,
        include_outliers=include_outliers,
    )
    click.echo(json.dumps(metrics, indent=2))
    click.echo(f"\nModel artifacts saved to {output}")

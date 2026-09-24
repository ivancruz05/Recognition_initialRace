"""Validate command - compare automatic results against ground truth."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import click

from drone_analysis.analysis.validation import ValidationAnalyzer


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


def _average_ground_truth(gt: Dict) -> Dict[str, float]:
    """Average non-null values per variable across all annotated frames."""
    frames: List[Dict] = gt.get("frames", [])
    averaged: Dict[str, float] = {}
    for var in gt.get("variables", []):
        values = [f[var] for f in frames if f.get(var) is not None]
        if values:
            averaged[var] = sum(values) / len(values)
    return averaged

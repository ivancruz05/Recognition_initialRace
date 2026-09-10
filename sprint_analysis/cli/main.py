"""Main CLI entry point."""

from __future__ import annotations

import click

from sprint_analysis.cli.commands.analyze import analyze
from sprint_analysis.cli.commands.measure import measure


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Sprint Start Analysis System.

    Analyze sprint start positions using Computer Vision and LiDAR.
    """
    pass


cli.add_command(measure)
cli.add_command(analyze)


if __name__ == "__main__":
    cli()

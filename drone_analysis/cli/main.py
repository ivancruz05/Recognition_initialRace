"""Main CLI entry point."""

from __future__ import annotations

import click

from drone_analysis.cli.commands.analyze import analyze
from drone_analysis.cli.commands.annotate import annotate
from drone_analysis.cli.commands.calibrate import calibrate
from drone_analysis.cli.commands.groundtruth import groundtruth
from drone_analysis.cli.commands.ml_generate import ml_generate
from drone_analysis.cli.commands.ml_train import ml_train
from drone_analysis.cli.commands.validate import validate


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Software de Análisis de Video por Drones Autónomos.

    Evalúa variables biomecánicas (postura, velocidad, zancada y cadencia)
    en videos de atletismo capturados con dron.
    """
    pass


cli.add_command(calibrate)
cli.add_command(analyze)
cli.add_command(annotate)
cli.add_command(groundtruth)
cli.add_command(validate)
cli.add_command(ml_generate)
cli.add_command(ml_train)


if __name__ == "__main__":
    cli()

"""CLI composition root - wires the detection and training modules together."""

from __future__ import annotations

import click

from detection.cli import register as register_detection
from training.cli import register as register_training


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Software de Análisis de Video por Drones Autónomos.

    Evalúa variables biomecánicas (postura, velocidad, zancada y cadencia)
    en videos de atletismo capturados con dron.
    """
    pass


register_detection(cli)
register_training(cli)


if __name__ == "__main__":
    cli()

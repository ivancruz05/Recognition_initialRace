"""Django model discovery entry point for the ``apps.sessions`` app.

``AppConfig.import_models()`` only looks for ``<app>.models``, while
this project keeps the real models in ``infrastructure/models.py``
(hexagonal layout). This module is therefore a one-line re-export: no
logic, no fields, just so the ORM and ``makemigrations`` can see the
models registered under the ``sessions`` app label.
"""

from .infrastructure.models import BiomechanicalMetricModel, SprintSessionModel

__all__ = ["SprintSessionModel", "BiomechanicalMetricModel"]

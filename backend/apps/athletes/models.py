"""Django model discovery entry point for the ``apps.athletes`` app.

``AppConfig.import_models()`` only looks for ``<app>.models``, while
this project keeps the real model in ``infrastructure/models.py``
(hexagonal layout). This module is therefore a one-line re-export: no
logic, no fields, just so the ORM and ``makemigrations`` can see the
model registered under the ``athletes`` app label.
"""

from .infrastructure.models import Athlete

__all__ = ["Athlete"]

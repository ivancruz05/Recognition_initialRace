"""Application layer of the athletes module.

Use cases plus their input/output DTOs. This package may import only
``backend.apps.athletes.domain`` and the standard library: no Django,
DRF, ``infrastructure/`` or ``interfaces/`` dependencies are allowed.
"""

from .dtos import AthleteOutput, CreateAthleteInput
from .use_cases import CreateAthlete, GetAthlete, ListAthletes

__all__ = [
    "AthleteOutput",
    "CreateAthleteInput",
    "CreateAthlete",
    "GetAthlete",
    "ListAthletes",
]

"""Domain layer of the athletes module.

Only stdlib imports are allowed in this package (no Django, DRF,
application/, infrastructure/ or interfaces/). The re-exports below are
safe: they only reference modules of this same layer.
"""

from .entities import Athlete
from .exceptions import AthleteNotFound, DomainError, InvalidAthleteData
from .repositories import AthleteRepository

__all__ = [
    "Athlete",
    "AthleteRepository",
    "DomainError",
    "InvalidAthleteData",
    "AthleteNotFound",
]

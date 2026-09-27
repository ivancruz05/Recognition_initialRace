"""Input and output DTOs for the athletes application layer.

Frozen dataclasses: they are plain data carriers crossing the boundary
toward ``interfaces/``. Domain entities are converted with
:meth:`AthleteOutput.from_entity` and never leave this layer.

Pure Python (stdlib + domain only): no Django, DRF or ORM types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..domain import Athlete, DomainError

__all__ = ["CreateAthleteInput", "AthleteOutput"]


@dataclass(frozen=True)
class CreateAthleteInput:
    """Payload required to create an athlete.

    Attributes:
        first_name: non-empty once stripped (domain-validated).
        last_name: non-empty once stripped (domain-validated).
        date_of_birth: real ``datetime.date``, not future, not before
            1900-01-01 (domain-validated).
    """

    first_name: str
    last_name: str
    date_of_birth: date


@dataclass(frozen=True)
class AthleteOutput:
    """Athlete representation returned to the interfaces layer.

    This DTO is the source of truth for the serializer in
    ``interfaces/``; the domain entity must not be exposed there.
    """

    id: int
    first_name: str
    last_name: str
    date_of_birth: date

    @classmethod
    def from_entity(cls, athlete: Athlete) -> "AthleteOutput":
        """Convert a persisted domain entity into this DTO.

        Args:
            athlete: entity already persisted by the repository
                (``id`` assigned).

        Returns:
            The equivalent output DTO.

        Raises:
            DomainError: if the repository returned an entity without
                an assigned ``id``, violating its contract.
        """
        if athlete.id is None:
            raise DomainError(
                "Athlete must be persisted (id assigned) before conversion "
                "to AthleteOutput"
            )
        return cls(
            id=athlete.id,
            first_name=athlete.first_name,
            last_name=athlete.last_name,
            date_of_birth=athlete.date_of_birth,
        )

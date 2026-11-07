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
    """Payload required to register an athlete (data contract, Tabla 8).

    Attributes:
        athlete_id: pseudonymous technical code (domain-validated).
        label: academic alias shown to the teacher, optional.
        group: semester / group, optional.
        registered_at: registration date; ``None`` means "today".
    """

    athlete_id: str
    label: str | None = None
    group: str | None = None
    registered_at: date | None = None


@dataclass(frozen=True)
class AthleteOutput:
    """Athlete representation returned to the interfaces layer.

    This DTO is the source of truth for the serializer in
    ``interfaces/``; the domain entity must not be exposed there.
    """

    id: int
    athlete_id: str
    label: str | None
    group: str | None
    registered_at: date

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
            athlete_id=athlete.athlete_id,
            label=athlete.label,
            group=athlete.group,
            registered_at=athlete.registered_at,
        )

"""Application use cases for the athletes module.

Each use case has a single responsibility and receives its repository
port (``AthleteRepository``) via constructor injection. Implementations
live in ``infrastructure/`` and are wired elsewhere: this module never
imports them.

Pure Python (stdlib + domain only): no Django, DRF or ORM.
"""

from __future__ import annotations

from datetime import date

from ..domain import Athlete, AthleteRepository
from .dtos import AthleteOutput, CreateAthleteInput

__all__ = ["CreateAthlete", "GetAthlete", "ListAthletes"]


class CreateAthlete:
    """Validate, persist and return a new athlete."""

    def __init__(self, repository: AthleteRepository) -> None:
        """Args:
            repository: persistence port injected by the caller.
        """
        self._repository = repository

    def execute(self, data: CreateAthleteInput) -> AthleteOutput:
        """Run the create-athlete flow.

        Args:
            data: input DTO with the athlete's technical data.

        Returns:
            The persisted athlete as an output DTO (with ``id``).

        Raises:
            InvalidAthleteData: if the input breaks a domain invariant
                (raised while constructing ``Athlete``).
        """
        athlete = Athlete(
            athlete_id=data.athlete_id,
            label=data.label,
            group=data.group,
            registered_at=data.registered_at or date.today(),
        )
        saved = self._repository.add(athlete)
        return AthleteOutput.from_entity(saved)


class GetAthlete:
    """Fetch a single athlete by its technical code."""

    def __init__(self, repository: AthleteRepository) -> None:
        self._repository = repository

    def execute(self, athlete_id: str) -> AthleteOutput:
        """Run the get-athlete flow.

        Raises:
            AthleteNotFound: propagated by the repository when no
                athlete matches ``athlete_id``.
        """
        athlete = self._repository.get_by_athlete_id(athlete_id)
        return AthleteOutput.from_entity(athlete)


class ListAthletes:
    """Return the athlete catalogue used to populate the filter selector.

    The docente (and the technical admin) receive the full catalogue; the
    endpoint that invokes this case is restricted by RBAC, so the case
    itself stays role-agnostic.
    """

    def __init__(self, repository: AthleteRepository) -> None:
        self._repository = repository

    def execute(self) -> list[AthleteOutput]:
        return [
            AthleteOutput.from_entity(athlete)
            for athlete in self._repository.list_all()
        ]

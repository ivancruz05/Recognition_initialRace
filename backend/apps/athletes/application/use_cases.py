"""Application use cases for the athletes module.

Each use case has a single responsibility and receives its repository
port (``AthleteRepository``) via constructor injection. Implementations
live in ``infrastructure/`` and are wired elsewhere: this module never
imports them.

Pure Python (stdlib + domain only): no Django, DRF or ORM.
"""

from __future__ import annotations

from ..domain import Athlete, AthleteRepository
from .dtos import AthleteOutput, CreateAthleteInput

__all__ = ["CreateAthlete", "GetAthlete"]


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
            data: input DTO with the athlete's personal data.

        Returns:
            The persisted athlete as an output DTO (with ``id``).

        Raises:
            InvalidAthleteData: if the input breaks a domain invariant
                (raised while constructing ``Athlete``).
        """
        athlete = Athlete(
            first_name=data.first_name,
            last_name=data.last_name,
            date_of_birth=data.date_of_birth,
        )
        saved = self._repository.add(athlete)
        return AthleteOutput.from_entity(saved)


class GetAthlete:
    """Fetch a single athlete by its identifier."""

    def __init__(self, repository: AthleteRepository) -> None:
        """Args:
            repository: persistence port injected by the caller.
        """
        self._repository = repository

    def execute(self, athlete_id: int) -> AthleteOutput:
        """Run the get-athlete flow.

        Args:
            athlete_id: identifier previously assigned on creation.

        Returns:
            The stored athlete as an output DTO.

        Raises:
            AthleteNotFound: propagated by the repository when no
                athlete matches ``athlete_id``.
        """
        athlete = self._repository.get_by_id(athlete_id)
        return AthleteOutput.from_entity(athlete)

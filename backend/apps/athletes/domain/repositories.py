"""Repository interfaces for the athletes domain.

Ports defined with the standard library only (``abc``). Concrete
implementations live in ``infrastructure/`` and are injected by the
application layer; the domain never imports them.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import Athlete


class AthleteRepository(ABC):
    """Persistence port for :class:`Athlete`.

    Only the operations required by the current use cases are declared
    (create, lookup by technical code, list for the filter catalogue).
    Adding a method later cannot break existing implementations.
    """

    @abstractmethod
    def add(self, athlete: Athlete) -> Athlete:
        """Persist a new athlete.

        The implementation must assign a positive ``id`` to the stored
        record and return the resulting ``Athlete``.

        Raises:
            InvalidAthleteData: if the datastore rejects the payload
                (including a duplicated ``athlete_id``).
        """

    @abstractmethod
    def get_by_athlete_id(self, athlete_id: str) -> Athlete:
        """Return the athlete with the given technical ``athlete_id``.

        Raises:
            AthleteNotFound: if no athlete matches. The repository must
                raise it, never return ``None``.
        """

    @abstractmethod
    def list_all(self) -> list[Athlete]:
        """Return every athlete ordered by technical code (filter catalogue)."""


__all__ = ["AthleteRepository"]

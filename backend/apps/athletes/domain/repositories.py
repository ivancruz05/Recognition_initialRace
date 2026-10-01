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

    Only the operations required by the current use cases
    (create athlete, get athlete) are declared. Update, delete and
    listing are deliberately absent: no use case needs them yet, and
    adding a method here later cannot break existing implementations.
    """

    @abstractmethod
    def add(self, athlete: Athlete) -> Athlete:
        """Persist a new athlete.

        The implementation must assign a positive ``id`` to the stored
        record and return the resulting ``Athlete`` (typically via
        ``dataclasses.replace(athlete, id=saved_id)`` or by setting
        ``athlete.id`` before returning it).

        Args:
            athlete: a valid, not-yet-persisted athlete (``id is None``).

        Returns:
            The same athlete with ``id`` assigned by the datastore.

        Raises:
            InvalidAthleteData: if the datastore rejects the payload.
        """

    @abstractmethod
    def get_by_id(self, athlete_id: int) -> Athlete:
        """Return the athlete with the given ``athlete_id``.

        Args:
            athlete_id: identifier previously assigned by :meth:`add`.

        Returns:
            The persisted athlete.

        Raises:
            AthleteNotFound: if no athlete exists with that id. The
                repository must raise it, never return ``None``.
        """


__all__ = ["AthleteRepository"]

"""Repository (outbound) ports for the sprint-session module.

Ports defined with the standard library only (``abc``). Concrete
implementations live in ``infrastructure/`` (Django ORM, in-memory mock)
and are injected by the application layer; the domain never imports them.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .entities import SprintSession

__all__ = ["SessionFilters", "SessionRepositoryPort"]


@dataclass(frozen=True)
class SessionFilters:
    """Immutable filter set applied by ``list`` (CU-02).

    Every field is optional; ``None`` means "do not filter by this key".
    The application layer is responsible for scoping the filters by role
    (a student only ever sees their own athlete).
    """

    athlete_id: Optional[str] = None
    session_id: Optional[str] = None
    test_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class SessionRepositoryPort(ABC):
    """Persistence port for :class:`SprintSession`.

    Only the operations required by the current use cases are declared;
    adding a method later cannot break existing implementations.
    """

    @abstractmethod
    def add(self, session: SprintSession) -> SprintSession:
        """Persist ``session`` (and its metrics) assigning a surrogate id.

        Raises:
            InvalidSessionData: if the datastore rejects the payload
                (including a duplicated ``session_id``).
        """

    @abstractmethod
    def get_by_id(self, session_id: str) -> SprintSession:
        """Return the session with the given business ``session_id``.

        Raises:
            SessionNotFound: if no session matches. Never returns None.
        """

    @abstractmethod
    def list(self, filters: SessionFilters) -> list[SprintSession]:
        """Return sessions matching ``filters``, newest first."""

    @abstractmethod
    def count_athletes(self, filters: SessionFilters) -> int:
        """Number of distinct athletes referenced by the matched sessions."""

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """True when ``session_id`` is already persisted."""

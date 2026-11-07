"""In-memory session repository (test double / driven adapter).

Implements ``SessionRepositoryPort`` without any persistence so the whole
hexagon (use cases + domain) can be exercised with zero Django, zero SQL
and zero HTTP (RNF-08, CP-07).
"""

from __future__ import annotations

from typing import Iterable, Optional

from ...domain import (
    InvalidSessionData,
    SessionFilters,
    SessionNotFound,
    SessionRepositoryPort,
    SprintSession,
)

__all__ = ["InMemorySessionRepository"]


class InMemorySessionRepository(SessionRepositoryPort):
    """Dictionary-backed implementation of the sessions port."""

    def __init__(self, sessions: Optional[Iterable[SprintSession]] = None) -> None:
        self._sessions: dict[str, SprintSession] = {}
        for session in sessions or []:
            self._sessions[session.session_id] = session

    # -- SessionRepositoryPort --------------------------------------------
    def add(self, session: SprintSession) -> SprintSession:
        if session.session_id in self._sessions:
            raise InvalidSessionData(
                "session_id {0!r} already exists".format(session.session_id),
                field="session_id",
            )
        session.id = len(self._sessions) + 1
        self._sessions[session.session_id] = session
        return session

    def get_by_id(self, session_id: str) -> SprintSession:
        try:
            return self._sessions[session_id]
        except KeyError:
            raise SessionNotFound(session_id)

    def list(self, filters: SessionFilters) -> list[SprintSession]:
        results = [
            session
            for session in self._sessions.values()
            if self._matches(session, filters)
        ]
        results.sort(key=lambda session: session.timestamp, reverse=True)
        return results

    def count_athletes(self, filters: SessionFilters) -> int:
        return len(
            {session.athlete_id for session in self.list(filters)}
        )

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _matches(session: SprintSession, filters: SessionFilters) -> bool:
        if filters.athlete_id and session.athlete_id != filters.athlete_id:
            return False
        if filters.session_id and session.session_id != filters.session_id:
            return False
        if filters.test_type and session.test_type.lower() != filters.test_type.lower():
            return False
        if filters.date_from and session.timestamp.date() < filters.date_from:
            return False
        if filters.date_to and session.timestamp.date() > filters.date_to:
            return False
        return True

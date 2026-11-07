"""Domain exceptions for the sprint-session module.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer.
"""

from __future__ import annotations

from typing import Mapping

__all__ = [
    "DomainError",
    "InvalidSessionData",
    "InvalidContractError",
    "SessionNotFound",
    "AccessDenied",
]


class DomainError(Exception):
    """Base class for every error raised by the sessions domain layer."""


class InvalidSessionData(DomainError):
    """Raised when a ``SprintSession`` (or one of its value objects)
    violates a domain invariant.

    Attributes:
        field: name of the offending field, when the error is tied to a
            single attribute; ``None`` otherwise.
        message: human readable explanation of the broken invariant.
    """

    def __init__(self, message: str, field: str = None) -> None:
        self.message = message
        self.field = field
        super().__init__(message)


class InvalidContractError(DomainError):
    """Raised when an incoming payload does not satisfy the data contract
    (Tabla 8): missing traceability keys, bad types, unparsable timestamp...

    The whole payload is rejected BEFORE touching the domain or the
    database (RF-01, RNF-03, CP-01).

    Attributes:
        errors: mapping ``field -> message`` with every violation found.
    """

    def __init__(self, errors: Mapping[str, str]) -> None:
        self.errors = dict(errors)
        message = "; ".join(
            "{0}: {1}".format(field, detail) for field, detail in self.errors.items()
        )
        super().__init__(message or "invalid contract")

    @classmethod
    def single(cls, field: str, message: str) -> "InvalidContractError":
        return cls({field: message})


class SessionNotFound(DomainError):
    """Raised when a session lookup does not match any persisted record.

    Attributes:
        session_id: the business key that failed the lookup.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session with session_id {session_id!r} not found")


class AccessDenied(DomainError):
    """Raised when the requester's role is not allowed to read a record.

    Applied by the use cases (RBAC, RF-02): a student may only read the
    sessions of their own linked athlete.

    Attributes:
        session_id: the session the requester tried to read.
        athlete_id: the athlete that owns the session.
    """

    def __init__(self, session_id: str, athlete_id: str) -> None:
        self.session_id = session_id
        self.athlete_id = athlete_id
        super().__init__(
            "Session {0!r} belongs to athlete {1!r}; the requester may not "
            "read it".format(session_id, athlete_id)
        )

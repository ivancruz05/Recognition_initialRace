"""Domain exceptions for the athletes module.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every error raised by the athletes domain layer.

    Catching ``DomainError`` is enough to translate any domain failure
    into an application/infrastructure response (e.g. HTTP 4xx).
    """


class InvalidAthleteData(DomainError):
    """Raised when an ``Athlete`` violates a domain invariant.

    Attributes:
        field: name of the offending field, when the error is tied to a
            single attribute; ``None`` otherwise.
        message: human readable explanation of the broken invariant.
    """

    def __init__(self, message: str, field: str = None) -> None:
        self.message = message
        self.field = field
        super().__init__(message)


class AthleteNotFound(DomainError):
    """Raised when an athlete lookup does not match any persisted record.

    Attributes:
        athlete_id: the technical code that failed the lookup.
    """

    def __init__(self, athlete_id: str) -> None:
        self.athlete_id = athlete_id
        super().__init__(f"Athlete with athlete_id {athlete_id!r} not found")


__all__ = ["AthleteNotFound", "DomainError", "InvalidAthleteData"]

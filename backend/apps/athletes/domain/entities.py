"""Domain entities for the athletes module.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer: dates are ``datetime.date``, not
``django.utils.timezone`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .exceptions import InvalidAthleteData


@dataclass
class Athlete:
    """An athlete of the racing team.

    Mutable on purpose: the repository assigns ``id`` after persisting
    (see ``AthleteRepository.add``). Every other attribute is validated
    at construction time; mutating them afterwards without re-validating
    is out of scope for the domain layer.

    Invariants (enforced in ``__post_init__``):
        * ``first_name`` / ``last_name``: ``str``, non-empty once
          stripped of surrounding whitespace.
        * ``date_of_birth``: a real ``datetime.date`` (not a string),
          not in the future and not before 1900-01-01.
        * ``id``: ``None`` before persistence, positive ``int`` after.

    Raises:
        InvalidAthleteData: if any invariant above is broken.
    """

    first_name: str
    last_name: str
    date_of_birth: date
    id: Optional[int] = None

    def __post_init__(self) -> None:
        self._validate_name("first_name", self.first_name)
        self._validate_name("last_name", self.last_name)
        self._validate_date_of_birth(self.date_of_birth)
        self._validate_id(self.id)

    # -- validation helpers -------------------------------------------------
    @staticmethod
    def _validate_name(field_name: str, value: str) -> None:
        if not isinstance(value, str):
            raise InvalidAthleteData(
                "{0} must be a str, got {1}".format(field_name, type(value).__name__),
                field=field_name,
            )
        if not value.strip():
            raise InvalidAthleteData(
                "{0} must not be empty".format(field_name),
                field=field_name,
            )

    @staticmethod
    def _validate_date_of_birth(value: date) -> None:
        # bool is a subclass of int, but a bool is never a valid date.
        if isinstance(value, bool) or not isinstance(value, date):
            raise InvalidAthleteData(
                "date_of_birth must be a datetime.date, got {0}".format(
                    type(value).__name__
                ),
                field="date_of_birth",
            )
        if value > date.today():
            raise InvalidAthleteData(
                "date_of_birth {0} is in the future".format(value.isoformat()),
                field="date_of_birth",
            )
        if value < date(1900, 1, 1):
            raise InvalidAthleteData(
                "date_of_birth {0} is before 1900-01-01".format(value.isoformat()),
                field="date_of_birth",
            )

    @staticmethod
    def _validate_id(value: Optional[int]) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise InvalidAthleteData(
                "id must be a positive int or None, got {0!r}".format(value),
                field="id",
            )


__all__ = ["Athlete"]

"""Domain entities for the athletes module.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer: dates are ``datetime.date``, not
``django.utils.timezone`` objects.

Aligned with the monograph data contract (Tabla 8): the athlete is
identified by a pseudonymous technical code (``athlete_id``), never by a
personal document, and the personal fields of the source system are not
imported (data minimization, Ley 1581 de 2012).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .exceptions import InvalidAthleteData

MAX_CODE_LENGTH = 64
MAX_LABEL_LENGTH = 120


@dataclass
class Athlete:
    """An athlete of the CADI, referenced by a pseudonymous code.

    Mutable on purpose: the repository assigns ``id`` after persisting
    (see ``AthleteRepository.add``). Every other attribute is validated
    at construction time.

    Invariants (enforced in ``__post_init__``):
        * ``athlete_id``: non-empty ``str`` up to ``MAX_CODE_LENGTH``
          (technical code, e.g. ``"ATL-1042"``);
        * ``label`` / ``group``: ``None`` or a non-empty ``str``;
        * ``registered_at``: a real ``datetime.date``, not in the future
          and not before 1900-01-01;
        * ``id``: ``None`` before persistence, positive ``int`` after.

    Raises:
        InvalidAthleteData: if any invariant above is broken.
    """

    athlete_id: str
    label: str | None = None
    group: str | None = None
    registered_at: date = field(default_factory=date.today)
    id: int | None = None

    def __post_init__(self) -> None:
        self._validate_code("athlete_id", self.athlete_id, MAX_CODE_LENGTH)
        self._validate_optional_text("label", self.label, MAX_LABEL_LENGTH)
        self._validate_optional_text("group", self.group, MAX_LABEL_LENGTH)
        self._validate_registered_at(self.registered_at)
        self._validate_id(self.id)

    # -- validation helpers -------------------------------------------------
    @staticmethod
    def _validate_code(field_name: str, value: str, max_length: int) -> None:
        if not isinstance(value, str):
            raise InvalidAthleteData(
                f"{field_name} must be a str, got {type(value).__name__}",
                field=field_name,
            )
        if not value.strip():
            raise InvalidAthleteData(
                f"{field_name} must not be empty",
                field=field_name,
            )
        if len(value) > max_length:
            raise InvalidAthleteData(
                f"{field_name} must be at most {max_length} chars",
                field=field_name,
            )

    @classmethod
    def _validate_optional_text(
        cls, field_name: str, value: str | None, max_length: int
    ) -> None:
        if value is None:
            return
        if not isinstance(value, str):
            raise InvalidAthleteData(
                f"{field_name} must be a str or None, got {type(value).__name__}",
                field=field_name,
            )
        if not value.strip():
            raise InvalidAthleteData(
                f"{field_name} must not be blank when provided",
                field=field_name,
            )
        if len(value) > max_length:
            raise InvalidAthleteData(
                f"{field_name} must be at most {max_length} chars",
                field=field_name,
            )

    @staticmethod
    def _validate_registered_at(value: date) -> None:
        # bool is a subclass of int, but a bool is never a valid date.
        if isinstance(value, bool) or not isinstance(value, date):
            raise InvalidAthleteData(
                f"registered_at must be a datetime.date, got {type(value).__name__}",
                field="registered_at",
            )
        if value > date.today():
            raise InvalidAthleteData(
                f"registered_at {value.isoformat()} is in the future",
                field="registered_at",
            )
        if value < date(1900, 1, 1):
            raise InvalidAthleteData(
                f"registered_at {value.isoformat()} is before 1900-01-01",
                field="registered_at",
            )

    @staticmethod
    def _validate_id(value: int | None) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise InvalidAthleteData(
                f"id must be a positive int or None, got {value!r}",
                field="id",
            )


__all__ = ["Athlete", "MAX_CODE_LENGTH", "MAX_LABEL_LENGTH"]

"""Django ORM implementation of the :class:`AthleteRepository` port.

Single point of contact between the pure domain layer and Django: domain
entities go in, ORM rows come out (and the other way round). Every other
public method of this package works with entities only.

Dependency rules (checked by @architecture-reviewer):
    * may import ``..domain`` (entity, port, domain exceptions) and
      Django/ORM;
    * must NOT import ``..application`` nor ``..interfaces``.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError

from ..domain import Athlete, AthleteNotFound, AthleteRepository, InvalidAthleteData
from .models import Athlete as AthleteModel

__all__ = ["DjangoAthleteRepository"]


def _translate_validation_error(exc: ValidationError) -> InvalidAthleteData:
    """Convert Django's ``ValidationError`` into the domain error type.

    Kept as a module level helper so the public API of the repository
    raises domain exceptions only (callers never see Django's error
    classes).
    """
    message_dict = getattr(exc, "message_dict", None)
    if message_dict:
        field = sorted(message_dict)[0]
        message = "{0}: {1}".format(field, "; ".join(message_dict[field]))
    else:
        field = None
        message = "; ".join(exc.messages)
    return InvalidAthleteData(message, field=field)


class DjangoAthleteRepository(AthleteRepository):
    """Concrete ``AthleteRepository`` backed by the Django ORM.

    Entity ↔ model mapping lives in the private ``_to_model`` /
    ``_to_entity`` helpers below; the public methods speak the domain
    language only (``Athlete``, ``AthleteNotFound``,
    ``InvalidAthleteData``).
    """

    def add(self, athlete: Athlete) -> Athlete:
        """Persist ``athlete`` and assign the database id to it.

        The very same entity instance is returned with ``id`` set: no
        copy, no second validation round (``Athlete.__post_init__``
        already ran when the caller built it).

        Raises:
            InvalidAthleteData: if the datastore rejects the payload
                (schema level: max length, not-null, duplicated
                ``athlete_id``...), translated from Django's
                ``ValidationError``. Domain invariants are not
                re-checked here.
        """
        instance = self._to_model(athlete)
        try:
            instance.full_clean()
            instance.save()
        except ValidationError as exc:
            raise _translate_validation_error(exc) from exc
        athlete.id = instance.pk
        return athlete

    def get_by_athlete_id(self, athlete_id: str) -> Athlete:
        """Return the athlete stored under the technical ``athlete_id``.

        Raises:
            AthleteNotFound: when no row matches. Never returns
                ``None``.
        """
        try:
            instance = AthleteModel.objects.get(athlete_id=athlete_id)
        except AthleteModel.DoesNotExist:
            raise AthleteNotFound(athlete_id)
        return self._to_entity(instance)

    def list_all(self) -> list[Athlete]:
        """Every athlete ordered by technical code."""
        instances = AthleteModel.objects.order_by("athlete_id")
        return [self._to_entity(instance) for instance in instances]

    # -- entity <-> model mapping ------------------------------------------
    @staticmethod
    def _to_model(athlete: Athlete) -> AthleteModel:
        """Domain entity -> unpersisted ORM instance (``id`` excluded)."""
        return AthleteModel(
            athlete_id=athlete.athlete_id,
            label=athlete.label,
            group=athlete.group,
            registered_at=athlete.registered_at,
        )

    @staticmethod
    def _to_entity(instance: AthleteModel) -> Athlete:
        """ORM instance -> domain entity (``registered_at`` is a date)."""
        return Athlete(
            athlete_id=instance.athlete_id,
            label=instance.label,
            group=instance.group,
            registered_at=instance.registered_at,
            id=instance.pk,
        )

"""factory_boy factories for the athletes module (DB-backed tests only).

Used by the API/infrastructure tests to seed rows; never imported by the
domain/application suites (those stay pure Python).
"""

from datetime import date

import factory

from apps.athletes.infrastructure.models import Athlete

__all__ = ["AthleteFactory"]


class AthleteFactory(factory.django.DjangoModelFactory):
    """Persisted ``Athlete`` row with plausible, domain-valid values."""

    class Meta:
        model = Athlete

    athlete_id = factory.Sequence(lambda n: "ATL-{0:04d}".format(n + 1))
    label = factory.Sequence(lambda n: "Atleta {0}".format(n))
    group = factory.Sequence(lambda n: "Grupo {0}".format(n))
    registered_at = date(2020, 5, 10)

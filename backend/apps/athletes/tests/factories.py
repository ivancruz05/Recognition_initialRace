"""factory_boy factories for the athletes module (DB-backed tests only).

Used by the API tests to seed rows for GET; never imported by the
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

    first_name = factory.Sequence(lambda n: "First{0}".format(n))
    last_name = factory.Sequence(lambda n: "Last{0}".format(n))
    date_of_birth = date(1995, 7, 21)

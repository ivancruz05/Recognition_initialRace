"""Django persistence model for the athletes module.

This is a persistence *detail*: the row that stores an
:class:`apps.athletes.domain.Athlete`. It is NOT the domain entity and
must never be passed across layers — ``repositories.py`` is the only
module allowed to translate between the two.

Layer rules: this module may import Django; it must never import
``application/`` or ``interfaces/``.
"""

from django.db import models


class Athlete(models.Model):
    """Database row for a member of the racing team.

    Field types mirror the domain invariants one-to-one
    (``first_name``/``last_name`` → non-empty strings,
    ``date_of_birth`` → a calendar date); no extra behaviour is added
    here, validation of business rules belongs to the domain layer.
    """

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    class Meta:
        verbose_name = "athlete"
        verbose_name_plural = "athletes"

    def __str__(self) -> str:
        return "{0} {1}".format(self.first_name, self.last_name)

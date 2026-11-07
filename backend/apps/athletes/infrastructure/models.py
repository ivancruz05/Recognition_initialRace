"""Django persistence model for the athletes module.

This is a persistence *detail*: the row that stores an
:class:`apps.athletes.domain.Athlete`. It is NOT the domain entity and
must never be passed across layers — ``repositories.py`` is the only
module allowed to translate between the two.

Layer rules: this module may import Django; it must never import
``application/`` or ``interfaces/``.

Table name follows the monograph logical model (``cadi_athlete``).
"""

from django.db import models


class Athlete(models.Model):
    """Database row for an athlete of the CADI.

    Field types mirror the domain invariants one-to-one (``athlete_id``
    is the unique technical code, ``label``/``group`` are optional);
    no personal document is stored (data minimization, Ley 1581 de 2012).
    """

    athlete_id = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=120, null=True, blank=True)
    group = models.CharField(max_length=120, null=True, blank=True)
    registered_at = models.DateField()

    class Meta:
        verbose_name = "athlete"
        verbose_name_plural = "athletes"
        db_table = "cadi_athlete"

    def __str__(self) -> str:
        return self.label or self.athlete_id

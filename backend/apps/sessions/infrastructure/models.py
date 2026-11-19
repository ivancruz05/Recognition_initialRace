"""Django persistence models for the sessions module.

Persistence *detail*: these rows store :class:`SprintSession` domain
entities. They must never cross the layer boundary — ``repositories.py``
is the only module allowed to translate between rows and entities.

Layer rules: this module may import Django; it must never import
``application/`` or ``interfaces/``.

Table names follow the monograph logical model (Cap. 8.6): every metric
column is nullable so the database represents absence faithfully and
never stores an implicit zero (RF-09).
"""

from django.db import models


class TrainingSessionModel(models.Model):
    """An individual training session belonging to one athlete."""

    ATTENDANCE_CHOICES = (
        ("present", "Presente"),
        ("absent", "Ausente"),
        ("excused", "Justificada"),
    )

    athlete = models.ForeignKey(
        "athletes.Athlete",
        on_delete=models.CASCADE,
        related_name="training_sessions",
    )
    timestamp = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField()
    training_type = models.CharField(max_length=120)
    attendance_status = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES)
    coach = models.CharField(max_length=150, blank=True, default="")
    location = models.CharField(max_length=150, blank=True, default="")
    follow_up_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "training session"
        verbose_name_plural = "training sessions"
        db_table = "cadi_trainingsession"
        ordering = ["-timestamp", "-id"]

    def __str__(self) -> str:
        return f"{self.training_type} · {self.athlete.athlete_id}"


class SprintSessionModel(models.Model):
    """``cadi_sprintsession``: one 10 m sprint test of the CADI."""

    session_id = models.CharField(max_length=64, unique=True)
    athlete = models.ForeignKey(
        "athletes.Athlete",
        on_delete=models.CASCADE,
        related_name="sprint_sessions",
    )
    training_session = models.ForeignKey(
        "sprint_sessions.TrainingSessionModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sprint_tests",
    )
    timestamp = models.DateTimeField()
    test_type = models.CharField(max_length=120)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "sprint session"
        verbose_name_plural = "sprint sessions"
        db_table = "cadi_sprintsession"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return self.session_id


class BiomechanicalMetricModel(models.Model):
    """``cadi_biomechanicalmetric``: the four domain variables per session.

    ``*_series`` stores the JSON list declared by the origin (or ``null``
    when the origin did not send one). NULL means "not captured"; it is
    never replaced by 0.
    """

    session = models.OneToOneField(
        SprintSessionModel,
        on_delete=models.CASCADE,
        related_name="metric_row",
    )

    posture_data = models.JSONField(null=True, blank=True)

    speed_avg = models.FloatField(null=True, blank=True)
    speed_max = models.FloatField(null=True, blank=True)
    speed_unit = models.CharField(max_length=32, blank=True, default="")
    speed_series = models.JSONField(null=True, blank=True)

    stride_avg = models.FloatField(null=True, blank=True)
    stride_max = models.FloatField(null=True, blank=True)
    stride_unit = models.CharField(max_length=32, blank=True, default="")
    stride_series = models.JSONField(null=True, blank=True)

    cadence_avg = models.FloatField(null=True, blank=True)
    cadence_unit = models.CharField(max_length=32, blank=True, default="")
    cadence_series = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "biomechanical metric"
        verbose_name_plural = "biomechanical metrics"
        db_table = "cadi_biomechanicalmetric"

    def __str__(self) -> str:
        return "metrics of {0}".format(self.session_id)

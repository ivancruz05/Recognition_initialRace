"""Persistence model for generated and teacher-reviewed recommendations."""

from django.conf import settings
from django.db import models


class RecommendationRecord(models.Model):
    """Auditable record for one recommendation result (HU-08/HU-09)."""

    class OutputStatus(models.TextChoices):
        GENERATED = "GENERATED", "Generada"
        INSUFFICIENT_DATA = "INSUFFICIENT_DATA", "Datos insuficientes"

    class ReviewStatus(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "Pendiente de revisión"
        APPROVED = "APPROVED", "Aprobada"
        REJECTED = "REJECTED", "Rechazada"
        NOT_REQUIRED = "NOT_REQUIRED", "No requiere revisión"

    recommendation_id = models.CharField(max_length=64, unique=True)
    fingerprint = models.CharField(max_length=64, unique=True)
    rule_id = models.CharField(max_length=32)
    message = models.TextField()
    evidence = models.JSONField(default=list)
    session_ids = models.JSONField(default=list)
    status = models.CharField(max_length=32, choices=OutputStatus.choices)
    review_state = models.CharField(
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING_REVIEW,
        db_index=True,
    )
    limits = models.TextField()
    dataset_version = models.CharField(max_length=80)
    model_version = models.CharField(max_length=80, null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generated_cadi_recommendations",
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reviewed_cadi_recommendations",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "cadi_recommendation"
        ordering = ("-generated_at", "recommendation_id")
        indexes = [
            models.Index(
                fields=("review_state", "-generated_at"),
                name="cadi_rec_review_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return "{0} ({1})".format(self.recommendation_id, self.review_state)

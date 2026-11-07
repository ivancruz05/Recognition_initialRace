"""Domain entities for the analytics module.

Pure Python (stdlib only): no Django, DRF or third-party imports.

The monograph separates three kinds of output (§8.8): descriptive
indicators, model estimates and recommendations built from documented
rules. This module models only the third one, and it does so without any
causal or clinical claim (RNF-10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Sequence

__all__ = [
    "RecommendationStatus",
    "ReviewState",
    "Recommendation",
    "LIMITS_DISCLAIMER",
    "DATASET_VERSION",
    "MODEL_VERSION",
]

# Versionado analítico (RNF-09): la versión del conjunto de datos se
# registra en cada salida; la del modelo queda en None mientras la
# evaluación empírica permanezca pendiente (Cap. 11.6).
DATASET_VERSION = "cadi-fase1-export-1.0.0"
MODEL_VERSION: Optional[str] = None

LIMITS_DISCLAIMER = (
    "Apoyo informativo para la revisión del docente. No es un diagnóstico "
    "médico ni una garantía de mejora postural; corresponde al criterio "
    "profesional evaluarlo con el contexto de entrenamiento (RNF-10)."
)


class RecommendationStatus(Enum):
    """State of a recommendation output."""

    GENERATED = "GENERATED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ReviewState(Enum):
    """Human-in-the-loop state: every recommendation starts pending the
    docente's review (monograph §8.7, tabla de recomendación)."""

    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True)
class Recommendation:
    """One traceable recommendation (RF-13 / RF-14).

    Attributes:
        recommendation_id: stable id inside one response.
        rule_id: identifier of the documented rule that produced it.
        message: comprehensible, non-deterministic wording.
        evidence: what was observed (variables, values, units).
        session_ids: origin records that support the output.
        status: ``GENERATED`` or ``INSUFFICIENT_DATA``.
        review_state: always starts as ``PENDING_REVIEW``.
        limits: interpretation limits shown with the message.
    """

    recommendation_id: str
    rule_id: str
    message: str
    evidence: tuple[str, ...]
    session_ids: tuple[str, ...]
    status: RecommendationStatus = RecommendationStatus.GENERATED
    review_state: ReviewState = ReviewState.PENDING_REVIEW
    limits: str = LIMITS_DISCLAIMER
    dataset_version: str = DATASET_VERSION
    model_version: Optional[str] = MODEL_VERSION
    generated_by: Optional[int] = None
    generated_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty str")
        if not isinstance(self.evidence, tuple) or not isinstance(
            self.session_ids, tuple
        ):
            raise ValueError("evidence and session_ids must be tuples")
        if not isinstance(self.review_state, ReviewState):
            raise ValueError("review_state must be a ReviewState")
        if self.review_state in (ReviewState.APPROVED, ReviewState.REJECTED):
            if self.reviewed_by is None or self.reviewed_at is None:
                raise ValueError("reviewed recommendations need reviewer and timestamp")
        elif self.reviewed_by is not None or self.reviewed_at is not None:
            raise ValueError("unreviewed recommendations cannot have review metadata")
        if self.status is RecommendationStatus.INSUFFICIENT_DATA:
            if self.review_state not in (ReviewState.NOT_REQUIRED, ReviewState.PENDING_REVIEW):
                raise ValueError("insufficient-data results cannot be approved or rejected")

    @classmethod
    def insufficient_data(
        cls, recommendation_id: str, session_ids: Sequence[str], reason: str
    ) -> "Recommendation":
        """Factory for the CP-11 / CP-12 case: no supported output."""
        return cls(
            recommendation_id=recommendation_id,
            rule_id="R-00",
            message=(
                "No es posible generar una recomendación con la información "
                "disponible: {0}".format(reason)
            ),
            evidence=("Sin variables disponibles en las sesiones consultadas",),
            session_ids=tuple(session_ids),
            status=RecommendationStatus.INSUFFICIENT_DATA,
            review_state=ReviewState.NOT_REQUIRED,
        )

"""Input and output DTOs for the analytics application layer.

Pure Python (stdlib + domain only): no Django, DRF or ORM types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..domain import DATASET_VERSION, LIMITS_DISCLAIMER, MODEL_VERSION, Recommendation

__all__ = [
    "DescriptiveSummaryDTO",
    "RecommendationDTO",
    "AnalyticsResultDTO",
]


@dataclass(frozen=True)
class DescriptiveSummaryDTO:
    """Descriptive analytics over the selected sessions (RF-11).

    Averages ignore absent values: a ``NOT_AVAILABLE`` metric never
    contributes a zero (RF-09).
    """

    sessions_analyzed: int
    athletes: tuple[str, ...]
    completeness: dict  # variable -> % of sessions where it is available
    averages: dict  # variable -> mean of available values | None
    min_max: dict  # variable -> (min, max) of available values | None


@dataclass(frozen=True)
class RecommendationDTO:
    recommendation_id: str
    rule_id: str
    message: str
    evidence: tuple[str, ...]
    session_ids: tuple[str, ...]
    status: str
    review_state: str
    limits: str
    dataset_version: str
    model_version: Optional[str]
    generated_by: Optional[int]
    generated_at: Optional[datetime]
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]

    @classmethod
    def from_entity(cls, recommendation: Recommendation) -> "RecommendationDTO":
        return cls(
            recommendation_id=recommendation.recommendation_id,
            rule_id=recommendation.rule_id,
            message=recommendation.message,
            evidence=recommendation.evidence,
            session_ids=recommendation.session_ids,
            status=recommendation.status.value,
            review_state=recommendation.review_state.value,
            limits=recommendation.limits,
            dataset_version=recommendation.dataset_version,
            model_version=recommendation.model_version,
            generated_by=recommendation.generated_by,
            generated_at=recommendation.generated_at,
            reviewed_by=recommendation.reviewed_by,
            reviewed_at=recommendation.reviewed_at,
            review_note=recommendation.review_note,
        )


@dataclass(frozen=True)
class AnalyticsResultDTO:
    """Full analytics response: descriptive block + recommendations.

    ``model_version`` stays ``None`` and ``evaluation.status`` reports
    ``PENDING_EVIDENCE`` while the predictive component has no empirical
    evaluation (monograph §11.6) — the API never claims accuracy it does
    not have (RF-12, RNF-11).
    """

    descriptive: DescriptiveSummaryDTO
    recommendations: tuple[RecommendationDTO, ...]
    dataset_version: str = DATASET_VERSION
    model_version: Optional[str] = MODEL_VERSION
    execution_status: str = "EXECUTED"
    limits: str = LIMITS_DISCLAIMER

    @property
    def evaluation(self) -> dict:
        return {
            "status": "PENDING_EVIDENCE",
            "note": (
                "El componente predictivo no tiene evaluación empírica "
                "registrada (sin base real, variable objetivo, partición ni "
                "métricas): no se reporta exactitud ni mejora postural."
            ),
        }

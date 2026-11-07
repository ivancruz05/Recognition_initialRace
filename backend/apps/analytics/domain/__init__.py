"""Domain layer of the analytics module.

Only stdlib imports are allowed in this package (no Django, DRF,
application/, infrastructure/ or interfaces/), plus the pure domain of
the sessions module (``apps.sessions.domain``) for the input type of the
recommendation port.
"""

from .entities import (
    DATASET_VERSION,
    LIMITS_DISCLAIMER,
    MODEL_VERSION,
    Recommendation,
    RecommendationStatus,
    ReviewState,
)
from .exceptions import (
    AnalyticsError,
    AnalyticsAccessDenied,
    NoSessionsToAnalyze,
    RecommendationAlreadyReviewed,
    RecommendationNotFound,
)
from .ports import RecommendationPort, RecommendationRepositoryPort

__all__ = [
    "DATASET_VERSION",
    "LIMITS_DISCLAIMER",
    "MODEL_VERSION",
    "AnalyticsError",
    "AnalyticsAccessDenied",
    "NoSessionsToAnalyze",
    "RecommendationAlreadyReviewed",
    "RecommendationNotFound",
    "Recommendation",
    "RecommendationPort",
    "RecommendationRepositoryPort",
    "RecommendationStatus",
    "ReviewState",
]

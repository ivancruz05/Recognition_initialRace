"""Application layer of the analytics module.

Use cases plus their input/output DTOs. This package may import only
domain layers (``apps.analytics.domain``, ``apps.sessions.domain``) and
sibling application DTOs — never Django, DRF, ``infrastructure/`` or
``interfaces/``.
"""

from .dtos import AnalyticsResultDTO, DescriptiveSummaryDTO, RecommendationDTO
from .use_cases import (
    GenerateRecommendations,
    GetAnalytics,
    ListRecommendations,
    ReviewRecommendation,
)

__all__ = [
    "AnalyticsResultDTO",
    "DescriptiveSummaryDTO",
    "RecommendationDTO",
    "GetAnalytics",
    "GenerateRecommendations",
    "ListRecommendations",
    "ReviewRecommendation",
]

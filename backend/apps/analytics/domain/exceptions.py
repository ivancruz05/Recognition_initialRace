"""Domain exceptions for the analytics module.

Pure Python (stdlib only). This module must never import Django, DRF or
any other project layer.
"""

from __future__ import annotations

__all__ = [
    "AnalyticsError",
    "NoSessionsToAnalyze",
    "AnalyticsAccessDenied",
    "RecommendationNotFound",
    "RecommendationAlreadyReviewed",
]


class AnalyticsError(Exception):
    """Base class for analytics domain failures."""


class NoSessionsToAnalyze(AnalyticsError):
    """Raised when the requester did not select any session to analyze."""

    def __init__(self) -> None:
        super().__init__("At least one session_id is required to run the analytics")


class AnalyticsAccessDenied(AnalyticsError):
    """Raised when a role attempts an analytics operation outside its policy."""

    def __init__(self, role: str, operation: str) -> None:
        self.role = role
        self.operation = operation
        super().__init__(
            "Role {0!r} may not {1}".format(role, operation)
        )


class RecommendationNotFound(AnalyticsError):
    """Raised when a review request references no persisted recommendation."""

    def __init__(self, recommendation_id: str) -> None:
        self.recommendation_id = recommendation_id
        super().__init__("Recommendation {0!r} not found".format(recommendation_id))


class RecommendationAlreadyReviewed(AnalyticsError):
    """A reviewed recommendation cannot be changed through the first-review API."""

    def __init__(self, recommendation_id: str) -> None:
        self.recommendation_id = recommendation_id
        super().__init__("Recommendation {0!r} has already been reviewed".format(recommendation_id))

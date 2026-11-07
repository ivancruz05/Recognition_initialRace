"""URL registration for the analytics module.

Mounted at ``api/v1/`` by the project orchestrator (``config/urls.py``):
the module only declares its own paths and never decides the prefix.
"""

from django.urls import path

from .views import (
    AnalyticsAPIView,
    RecommendationGenerateAPIView,
    RecommendationReviewAPIView,
)

__all__ = ["urlpatterns"]

urlpatterns = [
    path(
        "analytics/recommendations/generate/",
        RecommendationGenerateAPIView.as_view(),
        name="analytics-recommendations-generate",
    ),
    path(
        "analytics/recommendations/",
        AnalyticsAPIView.as_view(),
        name="analytics-recommendations",
    ),
    path(
        "analytics/recommendations/<str:recommendation_id>/review/",
        RecommendationReviewAPIView.as_view(),
        name="analytics-recommendation-review",
    ),
]

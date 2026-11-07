"""URL registration for the sessions module.

Mounted at ``api/v1/`` by the project orchestrator (``config/urls.py``):
the module only declares its own paths and never decides the prefix.
Static paths (``compare/``, ``ingest/``) are declared BEFORE the dynamic
``<session_id>/`` route so they are not swallowed by it.
"""

from django.urls import path

from .views import (
    DashboardSummaryView,
    SessionCompareAPIView,
    SessionDetailAPIView,
    SessionIngestAPIView,
    SessionListAPIView,
)

__all__ = ["urlpatterns"]

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("sessions/", SessionListAPIView.as_view(), name="session-list"),
    path("sessions/compare/", SessionCompareAPIView.as_view(), name="session-compare"),
    path("sessions/ingest/", SessionIngestAPIView.as_view(), name="session-ingest"),
    path(
        "sessions/<str:session_id>/",
        SessionDetailAPIView.as_view(),
        name="session-detail",
    ),
]

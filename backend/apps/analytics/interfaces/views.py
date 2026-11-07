"""DRF endpoints for descriptive analytics and reviewed recommendations."""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.interfaces.permissions import IsTeacher, IsTeacherOrStudent
from apps.sessions.domain.exceptions import AccessDenied, SessionNotFound
from apps.sessions.infrastructure.repositories import DjangoSessionRepository
from apps.sessions.interfaces.serializers import parse_requester
from apps.sessions.interfaces.views import translate_domain_error

from ..application import GenerateRecommendations, ListRecommendations, ReviewRecommendation
from ..domain import (
    AnalyticsAccessDenied,
    RecommendationAlreadyReviewed,
    RecommendationNotFound,
    ReviewState,
)
from ..infrastructure import DjangoRecommendationRepository, RuleBasedRecommendationAdapter
from .serializers import (
    AnalyticsResultSerializer,
    RecommendationGenerationSerializer,
    RecommendationReviewInputSerializer,
    parse_session_ids,
)

__all__ = [
    "AnalyticsAPIView",
    "RecommendationGenerateAPIView",
    "RecommendationReviewAPIView",
]


class AnalyticsCompositionAPIView(APIView):
    """Composition root: inject Django and rule-based adapters into use cases."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        sessions = DjangoSessionRepository()
        recommendations = DjangoRecommendationRepository()
        recommender = RuleBasedRecommendationAdapter()
        self._list_analytics = ListRecommendations(sessions, recommender, recommendations)
        self._generate_recommendations = GenerateRecommendations(
            sessions, recommender, recommendations
        )
        self._review_recommendation = ReviewRecommendation(recommendations)


def _validation_error(detail) -> Response:
    return Response(detail, status=status.HTTP_400_BAD_REQUEST)


def _session_error(exc: Exception) -> Response:
    return translate_domain_error(exc)


class AnalyticsAPIView(AnalyticsCompositionAPIView):
    """``GET /api/v1/analytics/recommendations/?ids=A,B``.

    Teachers see every review state; students see only APPROVED records whose
    complete set of source sessions belongs to them. The use case verifies
    session ownership before the repository returns any recommendation.
    """

    permission_classes = (IsTeacherOrStudent,)

    def get(self, request):
        try:
            session_ids = parse_session_ids(request.query_params)
        except serializers.ValidationError as exc:
            return _validation_error(exc.detail)

        requester = parse_requester(request.user)
        try:
            result = self._list_analytics.execute(session_ids, requester)
        except (SessionNotFound, AccessDenied) as exc:
            return _session_error(exc)
        except AnalyticsAccessDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            AnalyticsResultSerializer.to_representation(
                result, include_review_details=requester.role == "teacher"
            )
        )


class RecommendationGenerateAPIView(AnalyticsCompositionAPIView):
    """``POST /api/v1/analytics/recommendations/generate/`` (Docente only).

    Body: ``{"session_ids": ["SES-01", "SES-02"]}``. Generation is an
    explicit operation; results are persisted idempotently in PENDING_REVIEW.
    """

    permission_classes = (IsTeacher,)

    def post(self, request):
        serializer = RecommendationGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)

        requester = parse_requester(request.user)
        try:
            result = self._generate_recommendations.execute(
                serializer.validated_data["session_ids"],
                requester,
                generated_by=request.user.id,
            )
        except (SessionNotFound, AccessDenied) as exc:
            return _session_error(exc)
        except AnalyticsAccessDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            AnalyticsResultSerializer.to_representation(
                result, include_review_details=True
            ),
            status=status.HTTP_200_OK,
        )


class RecommendationReviewAPIView(AnalyticsCompositionAPIView):
    """``POST /api/v1/analytics/recommendations/{id}/review/`` (Docente only)."""

    permission_classes = (IsTeacher,)

    def post(self, request, recommendation_id: str):
        serializer = RecommendationReviewInputSerializer(data=request.data)
        if not serializer.is_valid():
            return _validation_error(serializer.errors)
        decision = ReviewState(serializer.validated_data["decision"])
        try:
            recommendation = self._review_recommendation.execute(
                recommendation_id=recommendation_id,
                decision=decision,
                requester=parse_requester(request.user),
                reviewer_id=request.user.id,
                note=serializer.validated_data.get("note"),
            )
        except RecommendationNotFound as exc:
            return Response(
                {"detail": str(exc), "recommendation_id": exc.recommendation_id},
                status=status.HTTP_404_NOT_FOUND,
            )
        except RecommendationAlreadyReviewed as exc:
            return Response(
                {"detail": str(exc), "recommendation_id": exc.recommendation_id},
                status=status.HTTP_409_CONFLICT,
            )
        except AnalyticsAccessDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            AnalyticsResultSerializer.recommendation(
                recommendation, include_review_details=True
            ),
            status=status.HTTP_200_OK,
        )

"""DRF views for the sessions module (HTTP ⇄ application use cases).

Composition root: the concrete driven adapters
(``DjangoSessionRepository``, ``DjangoAthleteRepository``,
``JsonContractValidator``) are instantiated here and injected into the
use cases. RBAC for students is applied inside the use cases; the HTTP
layer only translates domain errors into status codes.

Dependency rules (checked by @architecture-reviewer):
    * may import ``rest_framework``, ``..application``,
      ``..infrastructure.repositories`` / ``..infrastructure.
      contract_validator`` (composition only) and ``..domain.exceptions``
      (error translation);
    * must NOT touch ``..infrastructure.models``, the ORM or Django
      models directly.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.interfaces.permissions import IsTeacherOrAdmin
from apps.athletes.infrastructure.repositories import DjangoAthleteRepository

from ..application import (
    CompareSessions,
    GetDashboardSummary,
    GetSessionDetail,
    IngestSessionContract,
    ListSessionsByFilter,
)
from ..domain.exceptions import (
    AccessDenied,
    InvalidContractError,
    InvalidSessionData,
    SessionNotFound,
)
from ..infrastructure.contract_validator import JsonContractValidator
from ..infrastructure.repositories import DjangoSessionRepository
from .serializers import (
    ComparisonSerializer,
    DashboardSummarySerializer,
    IngestionResultSerializer,
    SessionDetailSerializer,
    SessionListItemSerializer,
    parse_filters,
    parse_requester,
)

__all__ = [
    "translate_domain_error",
    "DashboardSummaryView",
    "SessionListAPIView",
    "SessionDetailAPIView",
    "SessionCompareAPIView",
    "SessionIngestAPIView",
]


def translate_domain_error(exc: Exception) -> Response:
    """Translate the documented domain failures into HTTP responses."""
    if isinstance(exc, SessionNotFound):
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, AccessDenied):
        return Response(
            {
                "detail": "Acceso restringido: un estudiante solo puede consultar "
                "sus propias sesiones.",
                "session_id": exc.session_id,
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, (InvalidSessionData, InvalidContractError)):
        detail = getattr(exc, "message", None) or str(exc)
        payload = {"detail": detail}
        if getattr(exc, "field", None):
            payload["field"] = exc.field
        if getattr(exc, "errors", None):
            payload["errors"] = exc.errors
        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
    raise exc  # noqa: MDM01 - errores no documentados no se ocultan


class SessionsAPIView(APIView):
    """Base class holding the composition of every sessions use case."""

    permission_classes = (IsAuthenticated,)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        session_repository = DjangoSessionRepository()
        athlete_repository = DjangoAthleteRepository()
        self._list = ListSessionsByFilter(session_repository)
        self._summary = GetDashboardSummary(session_repository)
        self._detail = GetSessionDetail(session_repository)
        self._compare = CompareSessions(session_repository)
        self._ingest = IngestSessionContract(
            session_repository, athlete_repository, JsonContractValidator()
        )


class DashboardSummaryView(SessionsAPIView):
    """``GET /api/v1/dashboard/summary/`` (CU-01, RF-03/RF-04)."""

    def get(self, request):
        requester = parse_requester(request.user)
        filters = parse_filters(request.query_params, requester)
        try:
            summary = self._summary.execute(filters)
        except (SessionNotFound, AccessDenied, InvalidSessionData) as exc:
            return translate_domain_error(exc)
        return Response(DashboardSummarySerializer.to_representation(summary))


class SessionListAPIView(SessionsAPIView):
    """``GET /api/v1/sessions/`` (CU-02, HU-02/RF-04)."""

    def get(self, request):
        requester = parse_requester(request.user)
        filters = parse_filters(request.query_params, requester)
        try:
            items = self._list.execute(filters)
        except (SessionNotFound, AccessDenied, InvalidSessionData) as exc:
            return translate_domain_error(exc)
        return Response(
            [SessionListItemSerializer.to_representation(item) for item in items]
        )


class SessionDetailAPIView(SessionsAPIView):
    """``GET /api/v1/sessions/{session_id}/`` (CU-03, RF-05…RF-10)."""

    def get(self, request, session_id: str):
        requester = parse_requester(request.user)
        try:
            detail = self._detail.execute(session_id, requester)
        except (SessionNotFound, AccessDenied, InvalidSessionData) as exc:
            return translate_domain_error(exc)
        return Response(SessionDetailSerializer.to_representation(detail))


class SessionCompareAPIView(SessionsAPIView):
    """``GET /api/v1/sessions/compare/?ids=A,B`` (CU-04, HU-05)."""

    def get(self, request):
        ids_param = request.query_params.get("ids", "")
        session_ids = [item.strip() for item in ids_param.split(",") if item.strip()]
        if not session_ids:
            return Response(
                {"detail": "The 'ids' query parameter is required (comma separated).",
                 "field": "ids"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        requester = parse_requester(request.user)
        try:
            matrix = self._compare.execute(session_ids, requester)
        except (SessionNotFound, AccessDenied, InvalidSessionData) as exc:
            return translate_domain_error(exc)
        return Response(ComparisonSerializer.to_representation(matrix))


class SessionIngestAPIView(SessionsAPIView):
    """``POST /api/v1/sessions/ingest/`` (CU-05, RF-01, roles Docente/Admin).

    Body: one contract object or a list of them. The batch is atomic:
    any invalid record → 400 with the structured log and NOTHING written.
    """

    permission_classes = (IsAuthenticated, IsTeacherOrAdmin)

    def post(self, request):
        try:
            result = self._ingest.execute(request.data)
        except (InvalidContractError, InvalidSessionData) as exc:
            return translate_domain_error(exc)

        payload = IngestionResultSerializer.to_representation(result)
        if result.rejected > 0 or result.accepted == 0:
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_201_CREATED)

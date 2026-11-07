"""DRF view set for the athletes module (HTTP ⇄ application DTOs).

Composition root: ``DjangoAthleteRepository`` is instantiated here (the
only infrastructure dependency allowed in ``interfaces/``) and injected
into the application use cases. Each action delegates to a use case and
translates its exceptions into HTTP responses.

Endpoints (RBAC: Docente / Administrador):
    * ``GET    /api/v1/athletes/``            → catálogo para filtros
    * ``POST   /api/v1/athletes/``            → 201 / 400
    * ``GET    /api/v1/athletes/{athlete_id}/`` → 200 / 404

Dependency rules (checked by @architecture-reviewer):
    * may import ``rest_framework``, ``..application`` (use cases),
      ``..infrastructure.repositories`` (composition only) and
      ``..domain.exceptions`` (translation of failure modes);
    * must NOT touch ``..infrastructure.models``, the ORM or Django
      models directly.
"""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from ..application import CreateAthlete, GetAthlete, ListAthletes
from ..domain.exceptions import AthleteNotFound, InvalidAthleteData
from ..infrastructure.repositories import DjangoAthleteRepository
from apps.accounts.interfaces.permissions import IsTeacherOrAdmin
from .serializers import AthleteSerializer

__all__ = ["AthleteViewSet"]


class AthleteViewSet(viewsets.ViewSet):
    """List, create and retrieve athletes (teacher-facing catalogue)."""

    permission_classes = (IsTeacherOrAdmin,)

    def __init__(self, **kwargs) -> None:
        """Build the use cases with the concrete repository.

        This is the composition boundary: domain/application never see
        the ORM, and no other module instantiates the repository.
        """
        super().__init__(**kwargs)
        repository = DjangoAthleteRepository()
        self._create_athlete = CreateAthlete(repository)
        self._get_athlete = GetAthlete(repository)
        self._list_athletes = ListAthletes(repository)

    # -- actions -----------------------------------------------------------
    def list(self, request: Request) -> Response:
        """``GET /athletes/``: catálogo completo (selector de filtros)."""
        outputs = self._list_athletes.execute()
        return Response(
            [AthleteSerializer().to_representation(output) for output in outputs],
            status=status.HTTP_200_OK,
        )

    def create(self, request: Request) -> Response:
        """``POST /athletes/``: validate, persist and return the athlete.

        Returns:
            201 with the created ``AthleteOutput``, or 400 when the
            serializer rejects the payload (shape/type) or the domain
            rejects it (``InvalidAthleteData``, incl. código duplicado).
        """
        serializer = AthleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            output = self._create_athlete.execute(
                serializer.to_application_input(serializer.validated_data)
            )
        except InvalidAthleteData as exc:
            return Response(
                {"detail": exc.message, "field": exc.field},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            AthleteSerializer().to_representation(output),
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request: Request, pk: str) -> Response:
        """``GET /athletes/{athlete_id}/``: one athlete by technical code."""
        try:
            output = self._get_athlete.execute(pk)
        except AthleteNotFound as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            AthleteSerializer().to_representation(output),
            status=status.HTTP_200_OK,
        )

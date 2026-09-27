"""DRF view set for the athletes module (HTTP ⇄ application DTOs).

Composition root: ``DjangoAthleteRepository`` is instantiated here (the
only infrastructure dependency allowed in ``interfaces/``) and injected
into the application use cases. Each action delegates to a use case and
translates its exceptions into HTTP responses.

Dependency rules (checked by @architecture-reviewer):
    * may import ``rest_framework``, ``..application`` (use cases),
      ``..infrastructure.repositories`` (composition only) and
      ``..domain.exceptions`` (translation of the two documented
      failure modes below);
    * must NOT touch ``..infrastructure.models``, the ORM or Django
      models directly.
"""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from ..application import CreateAthlete, GetAthlete
from ..domain.exceptions import AthleteNotFound, InvalidAthleteData
from ..infrastructure.repositories import DjangoAthleteRepository
from .serializers import AthleteSerializer

__all__ = ["AthleteViewSet"]


class AthleteViewSet(viewsets.ViewSet):
    """Create and retrieve athletes.

    Implemented actions (and the only routes the router binds):

        * ``create`` → ``POST   /athletes/``        → 201 / 400
        * ``retrieve`` → ``GET   /athletes/{pk}/`` → 200 / 404

    ``list``, ``update``, ``partial_update`` and ``destroy`` are NOT
    implemented (out of scope). ``SimpleRouter.get_method_map`` keeps a
    route as long as *one* of its methods has a handler, therefore:

        * ``POST /athletes/`` is bound (create) while ``GET`` is not →
          ``GET /athletes/`` → 405;
        * the detail route binds ``GET`` only → ``PUT`` / ``PATCH`` /
          ``DELETE /athletes/{pk}/`` → 405.

    Verified with a real smoke test (Django test client), not assumed.
    """

    def __init__(self, **kwargs) -> None:
        """Build the use cases with the concrete repository.

        This is the composition boundary: domain/application never see
        the ORM, and no other module instantiates the repository.
        """
        super().__init__(**kwargs)
        repository = DjangoAthleteRepository()
        self._create_athlete = CreateAthlete(repository)
        self._get_athlete = GetAthlete(repository)

    # -- actions -----------------------------------------------------------
    def create(self, request: Request) -> Response:
        """``POST /athletes/``: validate, persist and return the athlete.

        Returns:
            201 with the created ``AthleteOutput``, or 400 when the
            serializer rejects the payload (shape/type) or the domain
            rejects it (``InvalidAthleteData``).
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
        """``GET /athletes/{pk}/``: return one athlete by id.

        Returns:
            200 with the ``AthleteOutput``; 404 when ``pk`` is not a
            positive integer or matches no persisted athlete
            (``AthleteNotFound``).
        """
        try:
            athlete_id = int(pk)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        try:
            output = self._get_athlete.execute(athlete_id)
        except AthleteNotFound as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            AthleteSerializer().to_representation(output),
            status=status.HTTP_200_OK,
        )

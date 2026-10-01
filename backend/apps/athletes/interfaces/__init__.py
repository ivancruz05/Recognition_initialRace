"""Interfaces layer (delivery) of the athletes module.

Only DRF serializers, views and router registration live here. This
package may import:

    * ``..application`` (DTOs and use cases) — always;
    * ``..infrastructure.repositories.DjangoAthleteRepository`` — only to
      compose the use cases at this boundary (the single allowed
      infrastructure dependency, the composition root);
    * ``..domain.exceptions`` — only to translate the two documented
      failure modes (``InvalidAthleteData``, ``AthleteNotFound``) into
      HTTP status codes.

It must NOT import domain entities, ``..infrastructure.models`` or any
ORM object: HTTP payloads are mapped to and from application DTOs only.
"""

__all__: list = []

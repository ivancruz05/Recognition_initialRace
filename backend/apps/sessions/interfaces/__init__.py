"""Interfaces layer (delivery) of the sessions module.

Only DRF serializers, views and URL registration live here. This package
may import:

    * ``..application`` (DTOs and use cases) — always;
    * ``..infrastructure.repositories`` / ``..infrastructure.
      contract_validator`` — only to compose the use cases at this
      boundary (the single allowed infrastructure dependency, the
      composition root);
    * ``..domain.exceptions`` — only to translate documented failure
      modes into HTTP status codes;
    * sibling modules' ``interfaces`` / ``infrastructure.repositories``
      for RBAC permissions and composition.

It must NOT import domain entities, ``..infrastructure.models`` or any
ORM object: HTTP payloads are mapped to and from application DTOs only.
"""

__all__: list = []

"""Interfaces layer (delivery) of the analytics module.

Only DRF serializers, views and URL registration live here. This package
may import:

    * ``..application`` (DTOs and use cases) — always;
    * ``..infrastructure`` — only to compose the use cases at this
      boundary (the single allowed infrastructure dependency, the
      composition root);
    * ``..domain.exceptions`` — only to translate documented failure
      modes into HTTP status codes;
    * sibling modules' ``interfaces`` / ``infrastructure.repositories``
      for RBAC context parsing and error translation.

It must NOT import domain entities, ``infrastructure.models`` or any
ORM object: HTTP payloads are mapped to and from application DTOs only.
"""

__all__: list = []

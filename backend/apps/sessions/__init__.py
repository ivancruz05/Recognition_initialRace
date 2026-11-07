"""Sprint-session module (hexagonal, CADI Fase II).

Layout follows the project convention:

    domain/          pure Python: entities, value objects, contract, ports
    application/     use cases + DTOs (depends on domain only)
    infrastructure/  driven adapters: Django ORM, JSON contract validator,
                     Fase I CSV export adapter, in-memory test double
    interfaces/      driving adapters: DRF views, serializers, URLs
"""

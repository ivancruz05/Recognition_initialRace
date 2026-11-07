"""Analytics module (hexagonal, CADI Fase II).

Descriptive analytics + traceable recommendations behind an outbound
port, so the method can be evaluated or replaced without touching the
domain, the use cases or the interface (monograph §8.8, RF-11…RF-14).

Layout::

    domain/          pure Python: Recommendation entity + port
    application/     use cases + DTOs (depends on domain + sessions domain)
    infrastructure/  driven adapter: documented rule-based recommender
    interfaces/      driving adapter: DRF view + URL
"""

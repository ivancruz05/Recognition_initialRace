"""Infrastructure layer of the athletes module.

Django ORM models, repository implementations and any future external
integration live here. Importing this package must stay cheap: the
``__init__.py`` deliberately re-exports nothing, so that importing a
single submodule never drags the whole layer (or Django's ORM) in.

Allowed dependencies: ``..domain`` (entity, port, domain exceptions)
plus Django/DRF/third-party SDKs. Forbidden: ``..application`` and
``..interfaces``.
"""

"""Test package for the athletes module (Clean Architecture suite).

Layer placement:
    * ``test_domain.py``      -> pure unit tests (no Django, no DB).
    * ``test_application.py`` -> unit tests with an in-memory fake repo.
    * ``test_api.py``         -> integration tests against the real URLs.
"""

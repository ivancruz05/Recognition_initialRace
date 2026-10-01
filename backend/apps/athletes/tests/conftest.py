"""Shared fixtures for the athletes test suite."""

import pytest
from rest_framework.test import APIClient

__all__ = ["api_client", "athlete_payload", "athlete_row"]


@pytest.fixture
def api_client():
    """DRF ``APIClient`` against the real project URLconf."""
    return APIClient()


@pytest.fixture
def athlete_payload():
    """Valid JSON body accepted by ``POST /api/v1/athletes/``."""
    return {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "date_of_birth": "2001-03-14",
    }


@pytest.fixture
def athlete_row():
    """A persisted athlete row (requires the ``django_db`` marker)."""
    from .factories import AthleteFactory

    return AthleteFactory()

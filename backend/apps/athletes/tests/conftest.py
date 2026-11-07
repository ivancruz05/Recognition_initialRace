"""Shared fixtures for the athletes test suite."""

import pytest
from rest_framework.test import APIClient

__all__ = ["api_client", "authenticate", "athlete_payload", "athlete_row"]

LOGIN_URL = "/api/v1/auth/login/"


@pytest.fixture
def api_client():
    """DRF ``APIClient`` against the real project URLconf."""
    return APIClient()


@pytest.fixture
def authenticate(api_client):
    """Create a user with an academic role and attach its Bearer token.

    Returns the created user so the test can assert on its fields.
    """

    def _authenticate(
        user_type="teacher",
        email=None,
        password="correct-horse-battery",
        **extra_fields,
    ):
        from apps.accounts.models import User

        email = email or "{0}@example.com".format(user_type)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="Rol",
            last_name=user_type.title(),
            user_type=user_type,
            **extra_fields,
        )
        response = api_client.post(
            LOGIN_URL, {"email": email, "password": password}, format="json"
        )
        assert response.status_code == 200, response.json()
        api_client.credentials(
            HTTP_AUTHORIZATION="Bearer {0}".format(response.json()["access"])
        )
        return user

    return _authenticate


@pytest.fixture
def athlete_payload():
    """Valid JSON body accepted by ``POST /api/v1/athletes/``."""
    return {
        "athlete_id": "ATL-0001",
        "label": "Ada L.",
        "group": "Grupo 3",
    }


@pytest.fixture
def athlete_row():
    """A persisted athlete row (requires the ``django_db`` marker)."""
    from .factories import AthleteFactory

    return AthleteFactory()

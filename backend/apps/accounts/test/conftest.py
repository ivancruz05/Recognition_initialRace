"""Shared fixtures for the accounts tests."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """DRF client using the project's actual URL configuration."""
    return APIClient()


@pytest.fixture
def account_payload():
    """Valid JSON accepted by the register endpoint."""
    return {
        "email": "ada@example.com",
        "password": "correct-horse-battery",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }


@pytest.fixture
def account_user(db):
    """A persisted user for authentication endpoint tests."""
    from apps.accounts.models import User

    return User.objects.create_user(
        email="ada@example.com",
        password="correct-horse-battery",
        first_name="Ada",
        last_name="Lovelace",
    )

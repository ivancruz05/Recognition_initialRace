"""Shared fixtures for the sessions test suite."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.athletes.domain import Athlete, AthleteNotFound
from apps.athletes.infrastructure.repositories import DjangoAthleteRepository
from apps.sessions.domain import build_session
from apps.sessions.infrastructure.repositories import DjangoSessionRepository

from .factories import make_contract

__all__ = ["api_client", "authenticate", "contract_payload", "seed_sessions"]

LOGIN_URL = "/api/v1/auth/login/"


@pytest.fixture
def api_client():
    """DRF ``APIClient`` against the real project URLconf."""
    return APIClient()


@pytest.fixture
def contract_payload():
    """Minimum valid contract payload (Tabla 8)."""
    return make_contract()


@pytest.fixture
def authenticate(api_client):
    """Create a user with an academic role and attach its Bearer token.

    ``athlete`` links a student to their pseudonymous athlete row (the
    RBAC scope of RF-02).
    """

    def _authenticate(
        user_type="teacher",
        athlete=None,
        email=None,
        password="correct-horse-battery",
    ):
        from apps.accounts.models import User

        email = email or "{0}@example.com".format(user_type)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name="Rol",
            last_name=user_type.title(),
            user_type=user_type,
            athlete=athlete,
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
def seed_sessions(db):
    """Persist contract payloads through the real ORM adapters.

    Returns the list of ``session_id`` in the given order. Athletes are
    created on demand, exactly like the ingestion use case does.
    """

    def _seed(*payloads):
        athletes = DjangoAthleteRepository()
        sessions = DjangoSessionRepository()
        seeded = []
        for payload in payloads:
            contract = build_session(payload)
            athlete_id = contract.session.athlete_id
            try:
                athletes.get_by_athlete_id(athlete_id)
            except AthleteNotFound:
                athletes.add(
                    Athlete(
                        athlete_id=athlete_id,
                        label=contract.athlete_label,
                        group=contract.athlete_group,
                        registered_at=contract.session.timestamp.date(),
                    )
                )
            sessions.add(contract.session)
            seeded.append(contract.session.session_id)
        return seeded

    return _seed

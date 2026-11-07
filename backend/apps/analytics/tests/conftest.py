"""Shared fixtures for analytics API tests."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.athletes.domain import Athlete, AthleteNotFound
from apps.athletes.infrastructure.repositories import DjangoAthleteRepository
from apps.sessions.domain import build_session
from apps.sessions.infrastructure.repositories import DjangoSessionRepository

from apps.sessions.tests.factories import make_contract


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticate(api_client):
    def _authenticate(role="teacher", athlete=None, email=None):
        from apps.accounts.models import User

        email = email or role + "@analytics.test"
        password = "secret-analytics-123"
        User.objects.create_user(
            email=email, password=password, user_type=role, athlete=athlete
        )
        response = api_client.post(
            "/api/v1/auth/login/", {"email": email, "password": password}, format="json"
        )
        api_client.credentials(HTTP_AUTHORIZATION="Bearer " + response.json()["access"])
        return response

    return _authenticate


@pytest.fixture
def seed_sessions(db):
    def _seed(*payloads):
        athlete_repository = DjangoAthleteRepository()
        session_repository = DjangoSessionRepository()
        for payload in payloads:
            contract = build_session(payload)
            try:
                athlete_repository.get_by_athlete_id(contract.session.athlete_id)
            except AthleteNotFound:
                athlete_repository.add(
                    Athlete(
                        athlete_id=contract.session.athlete_id,
                        label=None,
                        group=None,
                        registered_at=contract.session.timestamp.date(),
                    )
                )
            session_repository.add(contract.session)
    return _seed


@pytest.fixture
def contract():
    return make_contract()

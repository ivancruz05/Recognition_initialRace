"""End-to-end tests for the accounts HTTP endpoints."""

import pytest
from rest_framework import status

from apps.accounts.models import User


LOGIN_URL = "/api/v1/auth/login/"
REGISTER_URL = "/api/v1/auth/register/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"


@pytest.mark.django_db
def test_register_creates_user_returns_public_data_and_starts_session(
    api_client, account_payload
):
    response = api_client.post(REGISTER_URL, account_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["email"] == account_payload["email"]
    assert body["first_name"] == account_payload["first_name"]
    assert body["last_name"] == account_payload["last_name"]
    assert body["user_type"] == "customer"
    assert "password" not in body

    user = User.objects.get(email=account_payload["email"])
    assert user.check_password(account_payload["password"])
    assert api_client.get(ME_URL).status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_register_duplicate_email_returns_400(api_client, account_user, account_payload):
    account_payload["email"] = account_user.email

    response = api_client.post(REGISTER_URL, account_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_register_invalid_payload_returns_400_without_creating_user(
    api_client, account_payload
):
    account_payload["password"] = "short"

    response = api_client.post(REGISTER_URL, account_payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.json()
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_login_valid_credentials_returns_public_data_and_starts_session(
    api_client, account_user
):
    response = api_client.post(
        LOGIN_URL,
        {"email": account_user.email, "password": "correct-horse-battery"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == account_user.email
    assert "password" not in response.json()
    assert api_client.get(ME_URL).status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_login_invalid_credentials_returns_401(api_client, account_user):
    response = api_client.post(
        LOGIN_URL,
        {"email": account_user.email, "password": "wrong-password"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()


@pytest.mark.django_db
def test_me_without_session_returns_401(api_client):
    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "No autenticado."}


@pytest.mark.django_db
def test_logout_ends_session(api_client, account_user):
    login_response = api_client.post(
        LOGIN_URL,
        {"email": account_user.email, "password": "correct-horse-battery"},
        format="json",
    )
    assert login_response.status_code == status.HTTP_200_OK
    assert api_client.get(ME_URL).status_code == status.HTTP_200_OK

    logout_response = api_client.post(LOGOUT_URL, {}, format="json")

    assert logout_response.status_code == status.HTTP_200_OK
    assert api_client.get(ME_URL).status_code == status.HTTP_401_UNAUTHORIZED

"""End-to-end tests for the accounts HTTP endpoints (JWT contract)."""

import pytest
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User


LOGIN_URL = "/api/v1/auth/login/"
REGISTER_URL = "/api/v1/auth/register/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"


def _authorize(client, email, password):
    """Log in and attach the Bearer access token to ``client``."""
    response = client.post(
        LOGIN_URL, {"email": email, "password": password}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK, response.json()
    client.credentials(
        HTTP_AUTHORIZATION="Bearer {0}".format(response.json()["access"])
    )
    return response.json()


def _assert_profile(profile, payload, user_type):
    assert set(profile) == {
        "id",
        "email",
        "first_name",
        "last_name",
        "user_type",
        "athlete_id",
    }
    assert profile["email"] == payload["email"]
    assert profile["first_name"] == payload.get("first_name", "")
    assert profile["last_name"] == payload.get("last_name", "")
    assert profile["user_type"] == user_type
    assert profile["athlete_id"] is None


# -- register --------------------------------------------------------------


@pytest.mark.django_db
def test_register_returns_tokens_and_student_profile(api_client, account_payload):
    response = api_client.post(REGISTER_URL, account_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert set(body) == {"access", "refresh", "profile"}
    assert isinstance(body["access"], str)
    assert isinstance(body["refresh"], str)
    _assert_profile(body["profile"], account_payload, user_type="student")

    user = User.objects.get(email=account_payload["email"])
    assert user.check_password(account_payload["password"])
    assert user.user_type == "student"


@pytest.mark.django_db
def test_register_always_creates_a_student_even_if_role_is_sent(
    api_client, account_payload
):
    account_payload["user_type"] = "teacher"

    response = api_client.post(REGISTER_URL, account_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["profile"]["user_type"] == "student"
    assert User.objects.get(email=account_payload["email"]).user_type == "student"


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


# -- login -----------------------------------------------------------------


@pytest.mark.django_db
def test_login_returns_tokens_and_profile(api_client, account_user):
    response = api_client.post(
        LOGIN_URL,
        {"email": account_user.email, "password": "correct-horse-battery"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert set(body) == {"access", "refresh", "profile"}
    assert body["profile"]["email"] == account_user.email
    assert body["profile"]["user_type"] == "student"
    assert "password" not in body


@pytest.mark.django_db
def test_login_of_a_teacher_reports_the_teacher_role(api_client):
    User.objects.create_user(
        email="profe@example.com",
        password="correct-horse-battery",
        first_name="Profe",
        last_name="Docente",
        user_type="teacher",
    )

    response = api_client.post(
        LOGIN_URL,
        {"email": "profe@example.com", "password": "correct-horse-battery"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["profile"]["user_type"] == "teacher"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("missing@example.com", "correct-horse-battery"),
        ("ada@example.com", "wrong-password"),
    ],
)
def test_login_invalid_credentials_returns_401(api_client, account_user, email, password):
    response = api_client.post(
        LOGIN_URL, {"email": email, "password": password}, format="json"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()


# -- me --------------------------------------------------------------------


@pytest.mark.django_db
def test_me_without_token_returns_401(api_client):
    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "detail" in response.json()


@pytest.mark.django_db
def test_me_with_bearer_token_returns_the_profile(api_client, account_user):
    _authorize(api_client, account_user.email, "correct-horse-battery")

    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == account_user.pk
    assert body["email"] == account_user.email
    assert body["user_type"] == "student"
    assert "password" not in body


@pytest.mark.django_db
def test_me_with_garbage_token_returns_401(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-token")

    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_me_with_invalidated_access_token_returns_401(api_client, account_user):
    tokens = _authorize(
        api_client, account_user.email, "correct-horse-battery"
    )
    # Invalidar el refresh no invalida el access; en cambio, usar un
    # refresh como access sí debe fallar.
    api_client.credentials(HTTP_AUTHORIZATION="Bearer {0}".format(tokens["refresh"]))

    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# -- logout ----------------------------------------------------------------


@pytest.mark.django_db
def test_logout_blacklists_the_refresh_token(api_client, account_user):
    tokens = _authorize(
        api_client, account_user.email, "correct-horse-battery"
    )

    response = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

    assert response.status_code == status.HTTP_200_OK
    with pytest.raises(TokenError):
        RefreshToken(tokens["refresh"])


@pytest.mark.django_db
def test_logout_without_refresh_returns_400(api_client):
    response = api_client.post(LOGOUT_URL, {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "detail" in response.json()


@pytest.mark.django_db
def test_logout_twice_still_returns_200(api_client, account_user):
    tokens = _authorize(
        api_client, account_user.email, "correct-horse-battery"
    )
    first = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")
    second = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK

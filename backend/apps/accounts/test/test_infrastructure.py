"""Integration tests for the Django-backed accounts repository and JWT."""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.settings import api_settings

from apps.accounts.domain import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    UserAccount,
    UserNotFound,
)
from apps.accounts.infrastructure import (
    DjangoUserRepository,
    blacklist_refresh_token,
    issue_tokens,
)

User = get_user_model()


@pytest.mark.django_db
def test_add_persists_account_and_hashes_password_with_argon2():
    repository = DjangoUserRepository()
    account = UserAccount(
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
    )

    saved = repository.add(account, "correct-horse-battery")
    stored_user = User.objects.get(pk=saved.id)

    assert saved.id == stored_user.pk
    assert stored_user.email == "ada@example.com"
    assert stored_user.check_password("correct-horse-battery")
    assert not stored_user.check_password("wrong-password")
    assert identify_hasher(stored_user.password).algorithm == "argon2"


@pytest.mark.django_db
def test_add_rejects_an_email_that_already_exists(account_user):
    repository = DjangoUserRepository()
    account = UserAccount(
        email=account_user.email.upper(),
        first_name="Another",
        last_name="Account",
    )

    with pytest.raises(EmailAlreadyRegistered):
        repository.add(account, "another-password")


@pytest.mark.django_db
def test_exists_by_email_is_case_insensitive(account_user):
    repository = DjangoUserRepository()

    assert repository.exists_by_email(account_user.email.upper())
    assert not repository.exists_by_email("missing@example.com")


@pytest.mark.django_db
def test_verify_credentials_returns_domain_entity(account_user):
    account = DjangoUserRepository().verify_credentials(
        account_user.email,
        "correct-horse-battery",
    )

    assert isinstance(account, UserAccount)
    assert account.id == account_user.pk
    assert account.email == account_user.email
    assert not hasattr(account, "password")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("missing@example.com", "correct-horse-battery"),
        ("ada@example.com", "wrong-password"),
    ],
)
def test_verify_credentials_rejects_invalid_credentials(account_user, email, password):
    with pytest.raises(InvalidCredentials):
        DjangoUserRepository().verify_credentials(email, password)


@pytest.mark.django_db
def test_get_by_id_returns_entity_and_missing_id_raises(account_user):
    repository = DjangoUserRepository()

    account = repository.get_by_id(account_user.pk)

    assert account.id == account_user.pk
    assert account.email == account_user.email
    with pytest.raises(UserNotFound):
        repository.get_by_id(999999)


@pytest.mark.django_db
def test_new_account_defaults_to_the_student_role():
    repository = DjangoUserRepository()
    account = UserAccount(
        email="nuevo@example.com", first_name="Nuevo", last_name="Estudiante"
    )

    saved = repository.add(account, "correct-horse-battery")

    assert saved.user_type == "student"
    assert User.objects.get(pk=saved.id).user_type == "student"


@pytest.mark.django_db
def test_verify_credentials_exposes_the_linked_athlete_code():
    from apps.athletes.infrastructure.models import Athlete

    athlete = Athlete.objects.create(
        athlete_id="ATL-0001", registered_at=date(2026, 1, 15)
    )
    user = User.objects.create_user(
        email="ada@example.com",
        password="correct-horse-battery",
        first_name="Ada",
        last_name="Lovelace",
        user_type="student",
        athlete=athlete,
    )

    account = DjangoUserRepository().verify_credentials(
        user.email, "correct-horse-battery"
    )

    assert account.user_type == "student"
    assert account.athlete_id == "ATL-0001"


# -- JWT (SimpleJWT) -------------------------------------------------------


@pytest.mark.django_db
def test_issue_tokens_returns_access_and_refresh_for_the_user(account_user):
    tokens = issue_tokens(account_user)

    assert set(tokens) == {"access", "refresh"}
    # El access verifica como token de acceso; el refresh, como refresh.
    from rest_framework_simplejwt.tokens import AccessToken

    AccessToken(tokens["access"])
    RefreshToken(tokens["refresh"])


@pytest.mark.django_db
def test_blacklisted_refresh_token_cannot_be_used_again(account_user):
    tokens = issue_tokens(account_user)

    blacklist_refresh_token(tokens["refresh"])

    with pytest.raises(TokenError):
        RefreshToken(tokens["refresh"])


def test_simplejwt_uses_project_token_lifetimes_and_rotation_settings():
    assert api_settings.ACCESS_TOKEN_LIFETIME == timedelta(minutes=60)
    assert api_settings.REFRESH_TOKEN_LIFETIME == timedelta(days=7)
    assert api_settings.ROTATE_REFRESH_TOKENS is True
    assert api_settings.BLACKLIST_AFTER_ROTATION is True

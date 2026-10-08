"""Integration tests for the Django-backed accounts repository."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher

from apps.accounts.domain import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    UserAccount,
    UserNotFound,
)
from apps.accounts.infrastructure import DjangoUserRepository

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

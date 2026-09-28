"""Pure unit tests for accounts domain entities and exceptions."""

import pytest

from apps.accounts.domain import InvalidAccountData, UserAccount


def test_valid_account_defaults_to_customer_and_can_have_blank_names():
    account = UserAccount(email="ada@example.com", first_name="", last_name="")

    assert account.id is None
    assert account.user_type == "customer"
    assert account.first_name == ""
    assert account.last_name == ""


@pytest.mark.parametrize("email", ["", "missing-at", "@example.com", "ada@"])
def test_invalid_email_raises_account_data_error_with_email_field(email):
    with pytest.raises(InvalidAccountData) as exc_info:
        UserAccount(email=email, first_name="Ada", last_name="Lovelace")

    assert exc_info.value.field == "email"


@pytest.mark.parametrize(
    ("field_name", "overrides"),
    [
        ("first_name", {"first_name": 123}),
        ("last_name", {"last_name": None}),
    ],
)
def test_non_string_name_raises_account_data_error(field_name, overrides):
    data = {
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        **overrides,
    }

    with pytest.raises(InvalidAccountData) as exc_info:
        UserAccount(**data)

    assert exc_info.value.field == field_name


@pytest.mark.parametrize("user_type", ["operator", None, []])
def test_invalid_user_type_raises_account_data_error(user_type):
    with pytest.raises(InvalidAccountData) as exc_info:
        UserAccount(
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            user_type=user_type,
        )

    assert exc_info.value.field == "user_type"


@pytest.mark.parametrize("account_id", [0, -1, True, "1"])
def test_invalid_id_raises_account_data_error(account_id):
    with pytest.raises(InvalidAccountData) as exc_info:
        UserAccount(
            email="ada@example.com",
            first_name="Ada",
            last_name="Lovelace",
            id=account_id,
        )

    assert exc_info.value.field == "id"


def test_persisted_admin_account_is_valid():
    account = UserAccount(
        email="admin@example.com",
        first_name="Ada",
        last_name="Lovelace",
        user_type="admin",
        id=7,
    )

    assert account.id == 7
    assert account.user_type == "admin"

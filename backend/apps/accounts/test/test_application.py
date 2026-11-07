"""Unit tests for accounts use cases, using an in-memory repository fake."""

import pytest

from apps.accounts.application import AuthOutput, GetMe, Login, LoginInput, Register, RegisterInput
from apps.accounts.domain import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    UserAccount,
    UserNotFound,
    UserRepository,
)


class InMemoryUserRepository(UserRepository):
    """Fake repository that keeps entities and raw test credentials in memory."""

    def __init__(self):
        self.accounts = {}
        self.passwords = {}
        self.next_id = 1

    def add(self, user: UserAccount, password: str) -> UserAccount:
        user.id = self.next_id
        self.next_id += 1
        self.accounts[user.id] = user
        self.passwords[user.email] = password
        return user

    def verify_credentials(self, email: str, password: str) -> UserAccount:
        if self.passwords.get(email) != password:
            raise InvalidCredentials()
        for account in self.accounts.values():
            if account.email == email:
                return account
        raise InvalidCredentials()

    def get_by_id(self, user_id: int) -> UserAccount:
        try:
            return self.accounts[user_id]
        except KeyError:
            raise UserNotFound(user_id)

    def exists_by_email(self, email: str) -> bool:
        return email in self.passwords


def register_input(**overrides) -> RegisterInput:
    values = {
        "email": "ada@example.com",
        "password": "correct-horse-battery",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    values.update(overrides)
    return RegisterInput(**values)


def test_register_persists_and_returns_public_output():
    repository = InMemoryUserRepository()

    output = Register(repository).execute(register_input())

    assert output == AuthOutput(
        id=1,
        email="ada@example.com",
        first_name="Ada",
        last_name="Lovelace",
        user_type="student",
    )
    assert "password" not in output.__dataclass_fields__
    assert repository.passwords["ada@example.com"] == "correct-horse-battery"


def test_register_passes_the_requested_role_through():
    # The use case does not force a role: the public endpoint asks for
    # "student", the admin path may ask for teacher/admin.
    repository = InMemoryUserRepository()

    output = Register(repository).execute(
        register_input(email="profe@example.com", user_type="teacher")
    )

    assert output.user_type == "teacher"


def test_auth_output_carries_the_linked_pseudonymous_athlete_id():
    repository = InMemoryUserRepository()
    Register(repository).execute(register_input())
    repository.accounts[1].athlete_id = "ATL-0001"

    output = GetMe(repository).execute(1)

    assert output.athlete_id == "ATL-0001"


def test_register_rejects_existing_email():
    repository = InMemoryUserRepository()
    use_case = Register(repository)
    use_case.execute(register_input())

    with pytest.raises(EmailAlreadyRegistered):
        use_case.execute(register_input())

    assert len(repository.accounts) == 1


def test_login_returns_account_output_for_valid_credentials():
    repository = InMemoryUserRepository()
    Register(repository).execute(register_input())

    output = Login(repository).execute(
        LoginInput(email="ada@example.com", password="correct-horse-battery")
    )

    assert output.id == 1
    assert output.email == "ada@example.com"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("missing@example.com", "correct-horse-battery"),
        ("ada@example.com", "wrong-password"),
    ],
)
def test_login_rejects_invalid_credentials(email, password):
    repository = InMemoryUserRepository()
    Register(repository).execute(register_input())

    with pytest.raises(InvalidCredentials):
        Login(repository).execute(LoginInput(email=email, password=password))


def test_get_me_returns_the_requested_account():
    repository = InMemoryUserRepository()
    Register(repository).execute(register_input())

    output = GetMe(repository).execute(1)

    assert output.email == "ada@example.com"
    assert output.id == 1


def test_get_me_propagates_user_not_found():
    with pytest.raises(UserNotFound) as exc_info:
        GetMe(InMemoryUserRepository()).execute(404)

    assert exc_info.value.account_id == 404

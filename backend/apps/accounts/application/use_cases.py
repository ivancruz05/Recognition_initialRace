from __future__ import annotations

from ..domain import EmailAlreadyRegistered, UserAccount, UserRepository
from .dtos import AuthOutput, LoginInput, RegisterInput


class Login:
    # autenticacion y devolucion de la cuenta

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository  # el puerto, no django

    def execute(self, data: LoginInput) -> AuthOutput:
        user = self._repository.verify_credentials(
            data.email, data.password
        )  # -> InvalidCredentials
        return AuthOutput.from_entity(user)


class Register:
    # crea una nueva cuenta

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, data: RegisterInput) -> AuthOutput:
        if self._repository.exists_by_email(data.email):
            raise EmailAlreadyRegistered(data.email)

        user = UserAccount(
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
        )

        saved = self._repository.add(user, data.password)
        return AuthOutput.from_entity(saved)


class GetMe:
    """
    Devuelve la cuenta del usuario actual
    """

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def execute(self, user_id: int) -> AuthOutput:
        user = self._repository.get_by_id(user_id)
        return AuthOutput.from_entity(user)

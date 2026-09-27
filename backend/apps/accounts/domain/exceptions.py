"""
Domain exceptions for the accounts module

Pure python (stdlib only)

This module never import Django, DRF or any other project layer

"""

from __future__ import annotations


class DomainError(Exception):
    """
        Base class for every error raised by the accounts domain layer

        Catching ``DomainError`` is enough to translate any domain failure
    into an application/infrastructure response (e.g. HTTP 4xx).

    """


class InvalidAccountData(DomainError):
    """Accounts: lanza una excepcion cuando se incumple una regla o invariante del dominio perteneciente
    (accounts) field identifcia el campo responsable del error cuando la infracciones esta relacionada con una
    propiedad concreta.
    Message contiene la explicacion legible del motivo por el cual la regla fue incumplida, esto permite una correcta
    informacion del problema
    """

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field
        super().__init__(message)


class UserNotFound(DomainError):
    def __init__(self, account_id: int) -> None:
        self.account_id = account_id
        super().__init__(f"account with id {account_id} not found")


class InvalidCredentials(DomainError):
    def __init__(self, message: str = "Credenciales invalidas") -> None:
        self.message = message
        super().__init__(message)

    """
            Email o Password incorrectos:
            Mensaje unico con el proposito de evitar saber cual fue el que fallo
    """


class EmailAlreadyRegistered(DomainError):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"email {email} already registered")


__all__ = [
    "DomainError",
    "EmailAlreadyRegistered",
    "InvalidAccountData",
    "InvalidCredentials",
    "UserNotFound",
]

"""
Repository port for the accounts domain.

Ports defined with the standard library only (``abc``). The concrete
implementation lives in ``infrastructure/``; the domain never imports it.
"""

from __future__ import annotations

from abc import abstractmethod, ABC

from .entities import UserAccount


class UserRepository(ABC):
    # Persistence + Credentials port for :class:'useraacount'

    @abstractmethod
    def add(self, user: UserAccount, password: str) -> UserAccount:
        """Persist ``user`` with a hashed ``password`` and assign its id.

        Raises:
            EmailAlreadyRegistered: si el email ya existe.
            InvalidAccountData: si el datastore rechaza el registro.
        """

    @abstractmethod
    def verify_credentials(self, email: str, password: str) -> UserAccount:
        """Return the account only if email+password match.

        Raises:
            InvalidCredentials: siempre que fallen (email o password).
        """

    @abstractmethod
    def get_by_id(self, user_id: int) -> UserAccount:
        """Raises:
        UserNotFound: si ninguna cuenta coincide.
        """

    @abstractmethod
    def exists_by_email(self, email: str) -> bool:
        """True si ya hay una cuenta con ese email."""

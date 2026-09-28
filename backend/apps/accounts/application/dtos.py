from __future__ import annotations

from dataclasses import dataclass

from ..domain import DomainError, UserAccount


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str


@dataclass(frozen=True)
class RegisterInput:
    email: str
    password: str
    first_name: str
    last_name: str


@dataclass(frozen=True)
class AuthOutput:
    id: int
    email: str
    first_name: str
    last_name: str
    user_type: str

    @classmethod
    def from_entity(cls, user: UserAccount) -> AuthOutput:
        # Entidad persistida -> DTO de salida. La entidad nunca sale de la capa
        if user.id is None:
            raise DomainError(
                "UserAccount must be persisted before conversion to AuthOutput"
            )
        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            user_type=user.user_type,
        )

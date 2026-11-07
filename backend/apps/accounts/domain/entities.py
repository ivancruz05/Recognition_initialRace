from __future__ import annotations

from dataclasses import dataclass

from .exceptions import InvalidAccountData

USER_TYPES = {
    "admin",
    "teacher",
    "student",
}  #! Espejo del UserType (el modelo no se puede importar aca)


@dataclass
class UserAccount:
    email: str
    first_name: str
    last_name: str
    user_type: str = "student"
    athlete_id: str | None = None  # codigo seudoanonimo del atleta vinculado
    id: int | None = None

    def __post_init__(self) -> None:
        self._validate_name("first_name", self.first_name)
        self._validate_name("last_name", self.last_name)
        self._validate_userType(self.user_type)
        self._validate_email(self.email)
        self._validate_athlete_id(self.athlete_id)
        self._validate_id(self.id)

    # ----- Validaciones ----------------------------------------

    @staticmethod
    def _validate_name(field_name: str, value: str) -> None:
        # El modelo permite blank=True -> Una cadena vacia Valida, pero debe ser str
        if not isinstance(value, str):
            raise InvalidAccountData(
                f"{field_name} must be a str, got {type(value).__name__}",
                field=field_name,
            )

    @staticmethod
    def _validate_email(value: str) -> None:
        """
        Si la instancia no es un objeto de tipo str y no contiene un @ no se valida
        """

        if not isinstance(value, str) or "@" not in value:
            raise InvalidAccountData("Email must be a valid address", field="email")
        local, _, domain = value.partition("@")
        if not local or not domain:
            raise InvalidAccountData("email must be a valid address", field="email")

    @staticmethod
    def _validate_athlete_id(value: str | None) -> None:
        """El vinculo con atleta es opcional, pero si existe debe ser un codigo no vacio."""
        if value is None:
            return
        if not isinstance(value, str) or not value.strip():
            raise InvalidAccountData(
                "athlete_id must be a non-empty str or None", field="athlete_id"
            )

    @staticmethod
    def _validate_id(value: int | None) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise InvalidAccountData(
                f"id must be a possitve int or None, got {value!r}", field="id"
            )

    @staticmethod
    def _validate_userType(value: str) -> None:
        if not isinstance(value, str) or value not in USER_TYPES:
            raise InvalidAccountData(
                f"user_type must be one of {sorted(USER_TYPES)}", field="user_type"
            )


__all__ = ["UserAccount", "USER_TYPES"]

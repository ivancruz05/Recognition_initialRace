from __future__ import annotations

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from ..domain import (
    EmailAlreadyRegistered,
    InvalidAccountData,
    InvalidCredentials,
    UserAccount,
    UserNotFound,
    UserRepository,
)
from ..models import User as UserModel


class DjangoUserRepository(UserRepository):
    #! Adaptador Django del puerto UserRepository. Unico punto con ORM

    def add(self, user: UserAccount, password: str) -> UserAccount:
        if UserModel.objects.filter(email__iexact=user.email).exists():
            raise EmailAlreadyRegistered(user.email)

        try:
            # CustomUserManager.create_user: normaliza email y hashea el password
            instance = UserModel.objects.create_user(
                email=user.email,
                password=password,
                first_name=user.first_name,
                last_name=user.last_name,
            )
        except ValidationError as exc:
            raise InvalidAccountData("; ".join(exc.messages)) from exc
        user.id = instance.pk
        return user

    def verify_credentials(self, email: str, password: str) -> UserAccount:
        # ModelBackend: USERNAME_FIELD = "email" kwarg email=
        instance = authenticate(email=email, password=password)
        if instance is None or not instance.is_active:
            raise InvalidCredentials()  # Mensaje unico, sin decir cual fallo
        return self._to_entity(instance)

    def get_by_id(self, user_id: int) -> UserAccount:
        try:
            instance = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            raise UserNotFound(user_id)
        return self._to_entity(instance)

    def exists_by_email(self, email: str) -> bool:
        return UserModel.objects.filter(email__iexact=email).exists()

    @staticmethod
    def _to_entity(instance: UserModel) -> UserAccount:
        # ORM -> entidad domain. El hash y el resto del modelo no viajan

        return UserAccount(
            email=instance.email,
            first_name=instance.first_name,
            last_name=instance.last_name,
            user_type=instance.user_type,
            id=instance.pk,
        )

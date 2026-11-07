from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from ..application import GetMe, Login, Register
from ..domain import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    UserNotFound,
    InvalidAccountData,
)
from ..infrastructure import DjangoUserRepository, blacklist_refresh_token, issue_tokens
from ..models import User as UserModel
from .serializers import LoginSerializer, RegisterSerializer

__all__ = [
    "LoginView",
    "RegisterView",
    "LogOutView",
    "MeView",
]


def _profile(output) -> dict:
    """Perfil público de rol usado por el frontend (sin credenciales)."""
    return {
        "id": output.id,
        "email": output.email,
        "first_name": output.first_name,
        "last_name": output.last_name,
        "user_type": output.user_type,
        "athlete_id": output.athlete_id,
    }


class AccountsAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        repository = DjangoUserRepository()
        self._login = Login(repository)
        self._register = Register(repository)
        self._get_me = GetMe(repository)


class LoginView(AccountsAPIView):
    """``POST /api/v1/auth/login/`` (público).

    Emite los tokens JWT (access + refresh) y el perfil de rol
    (Docente / Estudiante / Administrador).
    """

    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        input_data = serializer.to_application_input(serializer.validated_data)

        try:
            output = self._login.execute(input_data)
        except InvalidCredentials:
            return Response(
                {"detail": "credenciales invalidas"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = issue_tokens(UserModel.objects.get(pk=output.id))
        return Response(
            {**tokens, "profile": _profile(output)},
            status=status.HTTP_200_OK,
        )


class RegisterView(AccountsAPIView):
    """``POST /api/v1/auth/register/`` (público). Crea la cuenta y emite tokens."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        input_data = serializer.to_application_input(serializer.validated_data)

        try:
            output = self._register.execute(input_data)
        except EmailAlreadyRegistered as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except InvalidAccountData as exc:
            detail = {"detail": exc.message}
            if exc.field:
                detail["field"] = exc.field
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)

        tokens = issue_tokens(UserModel.objects.get(pk=output.id))
        return Response(
            {**tokens, "profile": _profile(output)},
            status=status.HTTP_201_CREATED,
        )


class LogOutView(AccountsAPIView):
    """``POST /api/v1/auth/logout/`` (público).

    Body: ``{"refresh": "<refresh token>"}``. Lo revoca en el servidor
    (blacklist), de modo que el cliente no pueda rotarlo después.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "Falta el refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            blacklist_refresh_token(refresh)
        except TokenError:
            # Token inválido o ya revocado: el cliente ya no tiene sesión.
            return Response(
                {"detail": "Sesion cerrada."},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Sesion cerrada."},
            status=status.HTTP_200_OK,
        )


class MeView(AccountsAPIView):
    """``GET /api/v1/auth/me/``: perfil del usuario autenticado (JWT)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            output = self._get_me.execute(request.user.id)
        except UserNotFound:
            return Response(
                {"detail": "no autenticado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(_profile(output), status=status.HTTP_200_OK)

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..application import GetMe, Login, Register
from ..domain import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    UserNotFound,
    InvalidAccountData,
)
from ..infrastructure import DjangoUserRepository, login_user, logout_user
from .serializers import LoginSerializer, RegisterSerializer


class AccountsAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        repository = DjangoUserRepository()
        self._login = Login(repository)
        self._register = Register(repository)
        self._get_me = GetMe(repository)


class LoginView(AccountsAPIView):
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

        login_user(request, output.id)
        return Response(
            LoginSerializer(instance=output).data,
            status=status.HTTP_200_OK,
        )


class RegisterView(AccountsAPIView):
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

        login_user(request, output.id)  # auto login despues del registro
        return Response(
            RegisterSerializer(instance=output).data,
            status=status.HTTP_201_CREATED,
        )


class LogOutView(AccountsAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout_user(request)
        return Response(
            {"detail": "Sesion cerrada."},
            status=status.HTTP_200_OK,
        )


class MeView(AccountsAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            output = self._get_me.execute(request.user.id)
        except UserNotFound:
            return Response(
                {"detail": "no autenticado."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            LoginSerializer(instance=output).data,
            status=status.HTTP_200_OK,
        )

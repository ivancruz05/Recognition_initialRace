from django.contrib.auth import login, logout

from ..models import User as UserModel


def login_user(request, user_id: int) -> None:
    # Abre la sesion de Djangola vista pasa por el id de AuthOutput
    instance = UserModel.objects.get(pk=user_id)
    login(request, instance, backend="django.contrib.auth.backends.ModelBackend")


def logout_user(request) -> None:
    logout(request)

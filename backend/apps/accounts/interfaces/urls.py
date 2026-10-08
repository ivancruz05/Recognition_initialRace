from django.urls import path

from .views import LoginView, LogOutView, MeView, RegisterView

urlpatterns = [
    path("login/", LoginView.as_view(), name="accounts-login"),
    path("register/", RegisterView.as_view(), name="accounts-register"),
    path("logout/", LogOutView.as_view(), name="accounts-logout"),
    path("me/", MeView.as_view(), name="accounts-me"),
]

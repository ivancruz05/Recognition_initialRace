from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.interfaces.urls")),
    path("api/v1/", include("apps.athletes.interfaces.urls")),
    path("api/v1/", include("apps.sessions.interfaces.urls")),
    path("api/v1/", include("apps.analytics.interfaces.urls")),
]

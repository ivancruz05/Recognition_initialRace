from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sessions"
    # ``django.contrib.sessions`` already owns the ``sessions`` label, so
    # this module needs its own unique one.
    label = "sprint_sessions"
    verbose_name = "sesiones de sprint"

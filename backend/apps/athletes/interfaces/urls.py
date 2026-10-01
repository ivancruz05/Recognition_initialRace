"""Router registration for the athletes module.

Only the router lives here. Nothing is mounted at a project level: the
orchestrator decides the mount point with
``path("", include("apps.athletes.interfaces.urls"))`` (or any prefix)
in ``config/urls.py``.
"""

from rest_framework.routers import DefaultRouter

from .views import AthleteViewSet

__all__ = ["router", "urlpatterns"]

router = DefaultRouter()
router.register(r"athletes", AthleteViewSet, basename="athlete")

urlpatterns = router.urls

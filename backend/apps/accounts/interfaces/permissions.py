"""RBAC permission classes (DRF) for the CADI roles.

The roles live in ``apps.accounts`` (Docente / Estudiante /
Administrador técnico); these classes are the delivery-layer translation
of the monograph's RBAC rules (RF-02, RNF-04) and are shared by every
module's ``interfaces/`` layer.

Dependency rules: DRF only — no domain, application or ORM imports.
"""

from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

__all__ = [
    "IsTeacher",
    "IsTeacherOrStudent",
    "IsTeacherOrAdmin",
    "IsReadOnlyForStudents",
]


def _role(user) -> str:
    return getattr(user, "user_type", "") or ""


class IsTeacher(BasePermission):
    """Solo Docente: revisión y consulta de salidas analíticas (HU-08/09)."""

    message = "Requiere rol Docente. Las salidas analíticas no están disponibles para estudiantes ni soporte técnico."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and _role(user) == "teacher")


class IsTeacherOrStudent(BasePermission):
    """Docente: cualquier recomendación; Estudiante: solo aprobadas y propias."""

    message = "Requiere rol Docente o Estudiante."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and _role(user) in ("teacher", "student")
        )


class IsTeacherOrAdmin(BasePermission):
    """Docente y Administrador técnico: catálogo de atletas, ingestión y
    lectura global. Estudiante: denegado (403).
    """

    message = "Requiere rol Docente o Administrador."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and _role(user) in ("teacher", "admin")
        )


class IsReadOnlyForStudents(BasePermission):
    """Docente/Admin: todo (lectura y escritura). Estudiante: solo lectura.

    El alcance de los datos (solo sus propias sesiones) lo aplica el caso
    de uso según el rol; esta clase solo controla el método HTTP.
    """

    message = "El rol Estudiante tiene acceso de solo lectura."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if _role(user) in ("teacher", "admin"):
            return True
        return request.method in SAFE_METHODS

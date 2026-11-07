from django.db import models
from django.contrib.auth.models import AbstractUser

from .customUser import CustomUserManager


class UserType(models.TextChoices):
    """Roles académicos del CADI (RBAC).

    ``TEACHER`` (Docente): lectura global, comparación libre e ingestión.
    ``STUDENT`` (Estudiante): solo sus propios registros.
    ``ADMIN`` (Administrador técnico): soporte, configuración de la fuente
    de datos y administración de cuentas.
    """

    ADMIN = "admin", "Administrador"
    TEACHER = "teacher", "Docente"
    STUDENT = "student", "Estudiante"


class User(AbstractUser):
    username = None

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    user_type = models.CharField(
        max_length=20, choices=UserType.choices, default=UserType.STUDENT
    )

    # Vínculo opcional con el registro de atleta (seudónimo) del CADI:
    # permite que un Estudiante vea únicamente sus propias sesiones.
    athlete = models.ForeignKey(
        "athletes.Athlete",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
        verbose_name="atleta vinculado",
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    def __str__(self):
        return self.email

    @property
    def is_teacher(self) -> bool:
        """True para Docente y para el Administrador técnico."""
        return self.user_type in (UserType.TEACHER, UserType.ADMIN)

    @property
    def is_student(self) -> bool:
        return self.user_type == UserType.STUDENT

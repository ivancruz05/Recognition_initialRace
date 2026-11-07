"""Emisión y revocación de tokens JWT (SimpleJWT).

Reemplaza la sesión de Django: el backend es stateless y el cliente
envía ``Authorization: Bearer <access>`` en cada petición (RFC 7519).
"""

from __future__ import annotations

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

__all__ = ["issue_tokens", "blacklist_refresh_token"]


def issue_tokens(user) -> dict:
    """Devuelve ``{"access": ..., "refresh": ...}`` para ``user``.

    El rol (Docente / Estudiante / Administrador) viaja en el perfil del
    login y se relee de la base en cada petición; no se duplica en el
    payload para que un cambio de rol tenga efecto inmediato.
    """
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def blacklist_refresh_token(refresh_token: str) -> None:
    """Invalida un refresh token (logout).

    Raises:
        TokenError: si el token es inválido o ya estaba revocado; la vista
            lo traduce a una respuesta controlada sin bloquear el flujo.
    """
    RefreshToken(refresh_token).blacklist()

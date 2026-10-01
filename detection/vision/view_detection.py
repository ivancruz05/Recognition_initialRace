"""Detección de tipo de vista (frontal/perfil) a partir de landmarks 2D.

Usa la separación horizontal de hombros y caderas, y la diferencia
de profundidad (z) entre lados, para clasificar la cámara como:

- "front": separación X alta, poca diferencia Z → cámara de frente
- "profile": separación X baja, alta diferencia Z → cámara lateral
- "diagonal": caso intermedio → no apto para mediciones fiables
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from detection.vision.pose_constants import (
    VIEW_FRONT_SHOULDER_THRESHOLD,
    VIEW_PROFILE_Z_RATIO,
    VIEW_MIN_VISIBILITY,
)
from detection.vision import landmarks as lm


class ViewType(Enum):
    FRONT = "front"
    PROFILE = "profile"
    DIAGONAL = "diagonal"


@dataclass
class ViewResult:
    """Resultado de la detección de vista."""
    view_type: ViewType
    shoulder_separation: float  # distancia X normalizada entre hombros
    hip_separation: float       # distancia X normalizada entre caderas
    z_diff_shoulder: float      # diferencia Z absoluta entre hombros
    confidence: float           # 0-1, cuán seguro está de la clasificación

    @property
    def is_valid_for_measurements(self) -> bool:
        return self.view_type == ViewType.PROFILE

    @property
    def label(self) -> str:
        return self.view_type.value


def _visibility_ok(landmarks: np.ndarray, *indices: int) -> bool:
    """True si todos los índices tienen visibility por encima del umbral."""
    return all(landmarks[i, 3] >= VIEW_MIN_VISIBILITY for i in indices)


def detect_view(landmarks: np.ndarray) -> ViewResult:
    """
    Clasifica la vista de la cámara a partir de landmarks normalizados (33, 4).

    Args:
        landmarks: array (33, 4) con [x, y, z, visibility] normalizados.

    Returns:
        ViewResult con el tipo de vista y métricas.
    """
    # --- Validar que los landmarks necesarios estén visibles ---
    needed = [lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER, lm.LEFT_HIP, lm.RIGHT_HIP]
    if not _visibility_ok(landmarks, *needed):
        return ViewResult(
            view_type=ViewType.DIAGONAL,
            shoulder_separation=0.0,
            hip_separation=0.0,
            z_diff_shoulder=0.0,
            confidence=0.0,
        )

    # --- Métricas geométricas ---
    ls_x, rs_x = landmarks[lm.LEFT_SHOULDER, 0], landmarks[lm.RIGHT_SHOULDER, 0]
    lh_x, rh_x = landmarks[lm.LEFT_HIP, 0], landmarks[lm.RIGHT_HIP, 0]
    ls_z, rs_z = landmarks[lm.LEFT_SHOULDER, 2], landmarks[lm.RIGHT_SHOULDER, 2]

    shoulder_sep = abs(ls_x - rs_x)   # alta en frontal, baja en perfil
    hip_sep = abs(lh_x - rh_x)         # idem
    z_diff = abs(ls_z - rs_z)          # alta en perfil, baja en frontal

    # --- Clasificación ---
    # Frontal: hombros bien separados en X, poca diferencia en Z
    # Profile: hombros poco separados en X, alta diferencia en Z (profundidad)
    if shoulder_sep >= VIEW_FRONT_SHOULDER_THRESHOLD:
        # Podría ser frontal o diagonal — checar Z para desambiguar
        if z_diff < shoulder_sep * VIEW_PROFILE_Z_RATIO:
            view_type = ViewType.FRONT
            confidence = min(1.0, shoulder_sep / 0.3)
        else:
            view_type = ViewType.DIAGONAL
            confidence = 0.4
    else:
        # Hombros poco separados → perfil o diagonal
        if z_diff > shoulder_sep * VIEW_PROFILE_Z_RATIO:
            view_type = ViewType.PROFILE
            confidence = min(1.0, z_diff / 0.15) if z_diff > 0.02 else 0.3
        else:
            view_type = ViewType.DIAGONAL
            confidence = 0.3

    return ViewResult(
        view_type=view_type,
        shoulder_separation=shoulder_sep,
        hip_separation=hip_sep,
        z_diff_shoulder=z_diff,
        confidence=confidence,
    )

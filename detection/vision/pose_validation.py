"""Validación de calidad de pose para mediciones corporales.

Verifica que la pose detectada sea apta para extraer medidas fiables:
- Landmarks clave visibles
- Simetría aceptable (sin inclinación lateral excesiva)
- Miembros superiores e inferiores completos
- Vista compatible (perfil para longitudes, frontal para anchos)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from detection.vision.pose_constants import (
    MIN_KEY_LANDMARKS_VISIBLE,
    MAX_LATERAL_TILT,
    VIEW_MIN_VISIBILITY,
)
from detection.vision import landmarks as lm
from detection.vision.view_detection import ViewType, ViewResult


# Landmarks esenciales para mediciones corporales
_KEY_LANDMARKS = [
    lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER,
    lm.LEFT_HIP, lm.RIGHT_HIP,
    lm.LEFT_KNEE, lm.RIGHT_KNEE,
    lm.LEFT_ANKLE, lm.RIGHT_ANKLE,
]

# Landmarks para verificar miembros superiores
_UPPER_BODY = [
    lm.LEFT_SHOULDER, lm.RIGHT_SHOULDER,
    lm.LEFT_ELBOW, lm.RIGHT_ELBOW,
    lm.LEFT_WRIST, lm.RIGHT_WRIST,
]

# Landmarks para verificar miembros inferiores
_LOWER_BODY = [
    lm.LEFT_HIP, lm.RIGHT_HIP,
    lm.LEFT_KNEE, lm.RIGHT_KNEE,
    lm.LEFT_ANKLE, lm.RIGHT_ANKLE,
]


@dataclass
class ValidationResult:
    """Resultado de la validación de pose."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    visible_keypoints: int = 0
    total_keypoints: int = 8
    visibility_ratio: float = 0.0
    view: Optional[ViewResult] = None

    @property
    def score(self) -> float:
        """Puntuación 0-1 de calidad de la pose."""
        if not self.errors:
            return min(1.0, self.visibility_ratio * 0.6 + (self.view.confidence if self.view else 0) * 0.4)
        return 0.0


def validate_pose(
    landmarks: np.ndarray,
    required_view: ViewType = ViewType.PROFILE,
) -> ValidationResult:
    """
    Valida si una pose es apta para mediciones corporales.

    Args:
        landmarks: array (33, 4) con [x, y, z, visibility] normalizados.
        required_view: tipo de vista requerida para las mediciones.

    Returns:
        ValidationResult con errores y advertencias.
    """
    result = ValidationResult(is_valid=False)

    if landmarks is None or len(landmarks) < 33:
        result.errors.append("Landmarks insuficientes (se esperan 33 puntos)")
        return result

    # --- 1. Visibilidad de landmarks clave ---
    visible = sum(
        1 for idx in _KEY_LANDMARKS
        if landmarks[idx, 3] >= VIEW_MIN_VISIBILITY
    )
    result.visible_keypoints = visible
    result.total_keypoints = len(_KEY_LANDMARKS)
    result.visibility_ratio = visible / len(_KEY_LANDMARKS)

    if visible < MIN_KEY_LANDMARKS_VISIBLE:
        result.errors.append(
            f"Landmarks insuficientes: {visible}/{len(_KEY_LANDMARKS)} visibles "
            f"(mínimo {MIN_KEY_LANDMARKS_VISIBLE})"
        )

    # --- 2. Completeness por segmento ---
    upper_visible = sum(
        1 for idx in _UPPER_BODY
        if landmarks[idx, 3] >= VIEW_MIN_VISIBILITY
    )
    lower_visible = sum(
        1 for idx in _LOWER_BODY
        if landmarks[idx, 3] >= VIEW_MIN_VISIBILITY
    )

    if upper_visible < 4:
        result.warnings.append(
            f"Miembros superiores parcialmente visibles ({upper_visible}/6)"
        )

    if lower_visible < 4:
        result.warnings.append(
            f"Miembros inferiores parcialmente visibles ({lower_visible}/6)"
        )

    # --- 3. Inclinación lateral (simetría) ---
    if landmarks[lm.LEFT_SHOULDER, 3] >= VIEW_MIN_VISIBILITY and \
       landmarks[lm.RIGHT_SHOULDER, 3] >= VIEW_MIN_VISIBILITY:
        shoulder_y_diff = abs(
            landmarks[lm.LEFT_SHOULDER, 1] - landmarks[lm.RIGHT_SHOULDER, 1]
        )
        if shoulder_y_diff > MAX_LATERAL_TILT:
            result.errors.append(
                f"Inclinación lateral excesiva: {shoulder_y_diff:.3f} "
                f"(máximo {MAX_LATERAL_TILT})"
            )

    # --- 4. Tipo de vista ---
    from detection.vision.view_detection import detect_view
    view = detect_view(landmarks)
    result.view = view

    if view.view_type != required_view:
        expected_label = "perfil" if required_view == ViewType.PROFILE else "frontal"
        actual_label = {
            ViewType.FRONT: "frontal",
            ViewType.PROFILE: "perfil",
            ViewType.DIAGONAL: "diagonal",
        }[view.view_type]
        result.errors.append(
            f"Vista incorrecta: se detectó {actual_label}, "
            f"se requiere {expected_label}"
        )

    # --- 5. Decisión final ---
    result.is_valid = len(result.errors) == 0
    return result


def format_validation_report(result: ValidationResult) -> str:
    """Genera un reporte legible de la validación."""
    lines = []
    status = "VÁLIDA" if result.is_valid else "INVÁLIDA"
    lines.append(f"=== VALIDACIÓN DE POSE: {status} ===")
    lines.append(f"  Puntuación: {result.score:.0%}")
    lines.append(f"  Landmarks visibles: {result.visible_keypoints}/{result.total_keypoints}")
    lines.append(f"  Ratio de visibilidad: {result.visibility_ratio:.0%}")

    if result.view:
        lines.append(f"  Vista detectada: {result.view.label} "
                      f"(confianza: {result.view.confidence:.0%})")
        lines.append(f"  Separación hombros: {result.view.shoulder_separation:.3f}")
        lines.append(f"  Separación caderas: {result.view.hip_separation:.3f}")
        lines.append(f"  Diferencia Z hombros: {result.view.z_diff_shoulder:.3f}")

    if result.errors:
        lines.append("\n  ERRORES:")
        for e in result.errors:
            lines.append(f"    ❌ {e}")

    if result.warnings:
        lines.append("\n  ADVERTENCIAS:")
        for w in result.warnings:
            lines.append(f"    ⚠️  {w}")

    if not result.errors and not result.warnings:
        lines.append("\n  ✅ Pose apta para mediciones")

    return "\n".join(lines)

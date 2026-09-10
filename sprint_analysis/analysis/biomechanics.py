"""Biomechanical analysis of sprint start position."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from sprint_analysis.domain.models import (
    BiomechanicalAngles,
    PoseLandmarks,
    SprintMetrics,
)
from sprint_analysis.domain.constants import OPTIMAL_ANGLES


class BiomechanicsAnalyzer:
    """Calculate biomechanical metrics from pose landmarks."""

    def __init__(self, visibility_threshold: float = 0.5):
        self.visibility_threshold = visibility_threshold

    def analyze(self, landmarks: PoseLandmarks) -> SprintMetrics:
        """Analyze sprint start position from landmarks."""
        angles = self._calculate_angles(landmarks)
        quality = self._calculate_quality(angles)
        recommendations = self._generate_recommendations(angles)

        return SprintMetrics(
            quality_score=quality,
            angles=angles,
        )

    def _calculate_angles(self, landmarks: PoseLandmarks) -> BiomechanicalAngles:
        """Calculate all joint angles."""
        nose = landmarks.get_array(type("Idx", (), {"value": 0})())
        ls = landmarks.get_array(type("Idx", (), {"value": 11})())
        rs = landmarks.get_array(type("Idx", (), {"value": 12})())
        lh = landmarks.get_array(type("Idx", (), {"value": 23})())
        rh = landmarks.get_array(type("Idx", (), {"value": 24})())
        lk = landmarks.get_array(type("Idx", (), {"value": 25})())
        rk = landmarks.get_array(type("Idx", (), {"value": 26})())
        la = landmarks.get_array(type("Idx", (), {"value": 27})())
        ra = landmarks.get_array(type("Idx", (), {"value": 28})())
        lf = landmarks.get_array(type("Idx", (), {"value": 31})())
        rf = landmarks.get_array(type("Idx", (), {"value": 32})())

        mid_shoulder = (ls + rs) / 2 if ls is not None and rs is not None else None
        mid_hip = (lh + rh) / 2 if lh is not None and rh is not None else None

        return BiomechanicalAngles(
            left_knee=self._calc_angle(lh, lk, la),
            right_knee=self._calc_angle(rh, rk, ra),
            left_hip=self._calc_angle(ls, lh, lk),
            right_hip=self._calc_angle(rs, rh, rk),
            left_ankle=self._calc_angle(lk, la, lf),
            right_ankle=self._calc_angle(rk, ra, rf),
            trunk_angle=self._calc_trunk_angle(nose, mid_shoulder, mid_hip),
        )

    def _calc_angle(self, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        """Calculate angle at point b (in degrees)."""
        if any(p is None for p in [a, b, c]):
            return 0.0

        ba = a[:3] - b[:3]
        bc = c[:3] - b[:3]

        dot = np.dot(ba, bc)
        mag_ba = np.linalg.norm(ba)
        mag_bc = np.linalg.norm(bc)

        if mag_ba == 0 or mag_bc == 0:
            return 0.0

        cos_angle = np.clip(dot / (mag_ba * mag_bc), -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))

    def _calc_trunk_angle(
        self, nose: np.ndarray, shoulder: np.ndarray, hip: np.ndarray
    ) -> float:
        """Calculate trunk inclination angle."""
        if any(p is None for p in [nose, shoulder, hip]):
            return 0.0

        trunk_vector = shoulder[:3] - hip[:3]
        vertical = np.array([0, -1, 0])

        cos_angle = np.dot(trunk_vector, vertical) / (np.linalg.norm(trunk_vector) + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))

    def _calculate_quality(self, angles: BiomechanicalAngles) -> float:
        """Calculate position quality score (0-100)."""
        scores = []

        for knee in [angles.left_knee, angles.right_knee]:
            if 90 <= knee <= 120:
                scores.append(100)
            elif 70 <= knee < 90 or 120 < knee <= 140:
                scores.append(70)
            elif 50 <= knee < 70 or 140 < knee <= 160:
                scores.append(40)
            else:
                scores.append(20)

        for hip in [angles.left_hip, angles.right_hip]:
            if 45 <= hip <= 90:
                scores.append(100)
            elif 30 <= hip < 45 or 90 < hip <= 110:
                scores.append(70)
            elif 15 <= hip < 30 or 110 < hip <= 130:
                scores.append(40)
            else:
                scores.append(20)

        trunk = angles.trunk_angle
        if 15 <= trunk <= 45:
            scores.append(100)
        elif 5 <= trunk < 15 or 45 < trunk <= 60:
            scores.append(70)
        elif trunk < 5 or 60 < trunk <= 75:
            scores.append(40)
        else:
            scores.append(20)

        return float(np.mean(scores))

    def _generate_recommendations(self, angles: BiomechanicalAngles) -> List[str]:
        """Generate recommendations based on angles."""
        recs = []

        avg_knee = (angles.left_knee + angles.right_knee) / 2
        if avg_knee < 80:
            recs.append("Rodillas muy flexionadas. Extiende ligeramente para más potencia.")
        elif avg_knee > 130:
            recs.append("Rodillas poco flexionadas. Flexiona más para mejor impulso.")

        avg_hip = (angles.left_hip + angles.right_hip) / 2
        if avg_hip < 40:
            recs.append("Cadera muy cerrada. Abre más el ángulo de cadera.")
        elif avg_hip > 100:
            recs.append("Cadera muy abierta. Cierra más el ángulo.")

        trunk = angles.trunk_angle
        if trunk < 10:
            recs.append("Tronco muy vertical. Inclínate más hacia adelante.")
        elif trunk > 50:
            recs.append("Tronco muy inclinado. Endereza ligeramente.")

        if not recs:
            recs.append("Posición dentro de los rangos óptimos.")

        return recs

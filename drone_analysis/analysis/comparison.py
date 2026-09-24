"""Reference comparison against optimal sprint start positions."""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from drone_analysis.domain.models import (
    BiomechanicalAngles,
    ComparisonResult,
    PoseLandmarks,
    SprintMetrics,
)
from drone_analysis.domain.constants import OPTIMAL_ANGLES


class ReferenceComparator:
    """Compare measured angles against biomechanics literature references."""

    def __init__(self):
        self.optimal = OPTIMAL_ANGLES

    def compare(self, metrics: SprintMetrics, landmarks: PoseLandmarks = None) -> ComparisonResult:
        """Compare metrics against optimal reference using front/rear leg detection."""
        angles = metrics.angles
        deviations = {}
        recommendations = []

        # Detect front/rear leg if landmarks provided
        front_leg = "left"
        if landmarks is not None:
            from drone_analysis.analysis.biomechanics import BiomechanicsAnalyzer
            analyzer = BiomechanicsAnalyzer()
            front_leg, _ = analyzer.detect_front_rear_leg(landmarks)

        # Compare knee angles with front/rear specific ranges
        front_knee_opt = self.optimal.get("front_knee", (80, 100))
        rear_knee_opt = self.optimal.get("rear_knee", (110, 150))
        
        for name, value in [("left_knee", angles.left_knee), ("right_knee", angles.right_knee)]:
            is_front = (name == f"{front_leg}_knee")
            opt_min, opt_max = front_knee_opt if is_front else rear_knee_opt
            dev = self._calculate_deviation(value, opt_min, opt_max)
            deviations[name] = dev
            if abs(dev) > 15:
                leg_type = "delantera" if is_front else "trasera"
                recommendations.append(self._knee_recommendation(name, value, opt_min, opt_max, leg_type))

        # Compare hip angles with front/rear specific ranges
        front_hip_opt = self.optimal.get("front_hip", (45, 70))
        rear_hip_opt = self.optimal.get("rear_hip", (85, 115))
        
        for name, value in [("left_hip", angles.left_hip), ("right_hip", angles.right_hip)]:
            is_front = (name == f"{front_leg}_hip")
            opt_min, opt_max = front_hip_opt if is_front else rear_hip_opt
            dev = self._calculate_deviation(value, opt_min, opt_max)
            deviations[name] = dev
            if abs(dev) > 15:
                leg_type = "delantera" if is_front else "trasera"
                recommendations.append(self._hip_recommendation(name, value, opt_min, opt_max, leg_type))

        # Compare ankle angles with front/rear specific ranges
        front_ankle_opt = self.optimal.get("front_ankle", (70, 90))
        rear_ankle_opt = self.optimal.get("rear_ankle", (90, 110))
        
        for name, value in [("left_ankle", angles.left_ankle), ("right_ankle", angles.right_ankle)]:
            is_front = (name == f"{front_leg}_ankle")
            opt_min, opt_max = front_ankle_opt if is_front else rear_ankle_opt
            dev = self._calculate_deviation(value, opt_min, opt_max)
            deviations[name] = dev
            if abs(dev) > 15:
                leg_type = "delantera" if is_front else "trasera"
                recommendations.append(self._ankle_recommendation(name, value, opt_min, opt_max, leg_type))

        # Compare trunk angle (from horizontal)
        opt_min, opt_max = self.optimal["trunk"]
        dev = self._calculate_deviation(angles.trunk_angle, opt_min, opt_max)
        deviations["trunk"] = dev
        if abs(dev) > 10:
            recommendations.append(self._trunk_recommendation(angles.trunk_angle, opt_min, opt_max))

        # Overall score
        overall_score = 100 - np.mean([abs(d) for d in deviations.values()])

        return ComparisonResult(
            deviations=deviations,
            recommendations=[r for r in recommendations if r],
            overall_score=max(0, float(overall_score)),
        )

    def _calculate_deviation(self, value: float, opt_min: float, opt_max: float) -> float:
        """Calculate deviation from optimal range (positive = too high, negative = too low)."""
        if value < opt_min:
            return value - opt_min
        elif value > opt_max:
            return value - opt_max
        return 0.0

    def _knee_recommendation(self, name: str, value: float, opt_min: float, opt_max: float, leg_type: str) -> str:
        side = "izquierda" if "left" in name else "derecha"
        if value < opt_min:
            return f"Rodilla {side} ({leg_type}) muy flexionada ({value:.0f}°). Extiende a {opt_min}-{opt_max}°."
        return f"Rodilla {side} ({leg_type}) poco flexionada ({value:.0f}°). Flexiona a {opt_min}-{opt_max}°."

    def _hip_recommendation(self, name: str, value: float, opt_min: float, opt_max: float, leg_type: str) -> str:
        side = "izquierda" if "left" in name else "derecha"
        if value < opt_min:
            return f"Cadera {side} ({leg_type}) muy cerrada ({value:.0f}°). Abre a {opt_min}-{opt_max}°."
        return f"Cadera {side} ({leg_type}) muy abierta ({value:.0f}°). Cierra a {opt_min}-{opt_max}°."

    def _ankle_recommendation(self, name: str, value: float, opt_min: float, opt_max: float, leg_type: str) -> str:
        side = "izquierda" if "left" in name else "derecha"
        if value < opt_min:
            return f"Tobillo {side} ({leg_type}) muy flexionado ({value:.0f}°). Extiende a {opt_min}-{opt_max}°."
        return f"Tobillo {side} ({leg_type}) poco flexionado ({value:.0f}°). Flexiona a {opt_min}-{opt_max}°."

    def _trunk_recommendation(self, value: float, opt_min: float, opt_max: float) -> str:
        if value < opt_min:
            return f"Tronco muy vertical ({value:.0f}°). Inclina a {opt_min}-{opt_max}° desde horizontal."
        return f"Tronco muy inclinado ({value:.0f}°). Endereza a {opt_min}-{opt_max}° desde horizontal."

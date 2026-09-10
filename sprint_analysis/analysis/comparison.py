"""Reference comparison against optimal sprint start positions."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from sprint_analysis.domain.models import (
    BiomechanicalAngles,
    ComparisonResult,
    SprintMetrics,
)
from sprint_analysis.domain.constants import OPTIMAL_ANGLES


class ReferenceComparator:
    """Compare measured angles against biomechanics literature references."""

    def __init__(self):
        self.optimal = OPTIMAL_ANGLES

    def compare(self, metrics: SprintMetrics) -> ComparisonResult:
        """Compare metrics against optimal reference."""
        angles = metrics.angles
        deviations = {}
        recommendations = []

        # Compare knee angles
        for name, value in [("left_knee", angles.left_knee), ("right_knee", angles.right_knee)]:
            opt_min, opt_max = self.optimal["knee"]
            dev = self._calculate_deviation(value, opt_min, opt_max)
            deviations[name] = dev
            if abs(dev) > 20:
                recommendations.append(self._knee_recommendation(name, value, opt_min, opt_max))

        # Compare hip angles
        for name, value in [("left_hip", angles.left_hip), ("right_hip", angles.right_hip)]:
            opt_min, opt_max = self.optimal["hip"]
            dev = self._calculate_deviation(value, opt_min, opt_max)
            deviations[name] = dev
            if abs(dev) > 20:
                recommendations.append(self._hip_recommendation(name, value, opt_min, opt_max))

        # Compare trunk angle
        opt_min, opt_max = self.optimal["trunk"]
        dev = self._calculate_deviation(angles.trunk_angle, opt_min, opt_max)
        deviations["trunk"] = dev
        if abs(dev) > 15:
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

    def _knee_recommendation(self, name: str, value: float, opt_min: float, opt_max: float) -> str:
        side = "izquierda" if "left" in name else "derecha"
        if value < opt_min:
            return f"Rodilla {side} muy flexionada ({value:.0f}°). Extiende a {opt_min}-{opt_max}°."
        return f"Rodilla {side} poco flexionada ({value:.0f}°). Flexiona a {opt_min}-{opt_max}°."

    def _hip_recommendation(self, name: str, value: float, opt_min: float, opt_max: float) -> str:
        side = "izquierda" if "left" in name else "derecha"
        if value < opt_min:
            return f"Cadera {side} muy cerrada ({value:.0f}°). Abre a {opt_min}-{opt_max}°."
        return f"Cadera {side} muy abierta ({value:.0f}°). Cierra a {opt_min}-{opt_max}°."

    def _trunk_recommendation(self, value: float, opt_min: float, opt_max: float) -> str:
        if value < opt_min:
            return f"Tronco muy vertical ({value:.0f}°). Inclina a {opt_min}-{opt_max}°."
        return f"Tronco muy inclinado ({value:.0f}°). Endereza a {opt_min}-{opt_max}°."

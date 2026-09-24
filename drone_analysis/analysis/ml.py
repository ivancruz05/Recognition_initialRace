"""ML-based analysis and predictions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from drone_analysis.domain.models import BiomechanicalAngles, SprintMetrics


@dataclass
class MLFeatures:
    """Features for ML prediction."""
    avg_knee_angle: float = 0.0
    avg_hip_angle: float = 0.0
    trunk_angle: float = 0.0
    knee_symmetry: float = 0.0
    hip_symmetry: float = 0.0
    height_cm: float = 0.0
    weight_kg: float = 0.0
    age: int = 0
    sex: str = "M"
    experience_years: int = 0


class MLAnalyzer:
    """Machine learning-based sprint analysis."""

    def __init__(self):
        self.model = None

    def extract_features(
        self,
        metrics: SprintMetrics,
        height_cm: float = 0,
        weight_kg: float = 0,
        age: int = 0,
        sex: str = "M",
        experience_years: int = 0,
    ) -> MLFeatures:
        """Extract features from metrics for ML prediction."""
        angles = metrics.angles

        return MLFeatures(
            avg_knee_angle=(angles.left_knee + angles.right_knee) / 2,
            avg_hip_angle=(angles.left_hip + angles.right_hip) / 2,
            trunk_angle=angles.trunk_angle,
            knee_symmetry=abs(angles.left_knee - angles.right_knee),
            hip_symmetry=abs(angles.left_hip - angles.right_hip),
            height_cm=height_cm,
            weight_kg=weight_kg,
            age=age,
            sex=sex,
            experience_years=experience_years,
        )

    def predict(self, features: MLFeatures) -> Dict:
        """Make predictions based on features (rule-based for now)."""
        predictions = {
            "quality_score": self._predict_quality(features),
            "common_errors": self._detect_errors(features),
            "recommendations": self._generate_recommendations(features),
        }
        return predictions

    def _predict_quality(self, features: MLFeatures) -> float:
        """Predict sprint quality (0-10)."""
        score = 5.0

        if 90 <= features.avg_knee_angle <= 120:
            score += 1.5
        elif features.avg_knee_angle < 70 or features.avg_knee_angle > 140:
            score -= 1.5

        if 45 <= features.avg_hip_angle <= 90:
            score += 1.5
        elif features.avg_hip_angle < 30 or features.avg_hip_angle > 110:
            score -= 1.5

        if 15 <= features.trunk_angle <= 45:
            score += 1.0
        elif features.trunk_angle < 5 or features.trunk_angle > 60:
            score -= 1.0

        if features.knee_symmetry > 15:
            score -= 0.5
        if features.hip_symmetry > 15:
            score -= 0.5

        return max(0, min(10, score))

    def _detect_errors(self, features: MLFeatures) -> List[str]:
        """Detect common sprint start errors."""
        errors = []

        if features.avg_knee_angle < 70:
            errors.append("过度屈膝")
        elif features.avg_knee_angle > 140:
            errors.append("膝关节伸展不足")

        if features.avg_hip_angle < 30:
            errors.append("髋关节过屈")
        elif features.avg_hip_angle > 110:
            errors.append("髋关节过伸")

        if features.trunk_angle < 5:
            errors.append("躯干过于直立")
        elif features.trunk_angle > 60:
            errors.append("躯干过度前倾")

        if features.knee_symmetry > 15:
            errors.append("双膝不对称")

        return errors

    def _generate_recommendations(self, features: MLFeatures) -> List[str]:
        """Generate personalized recommendations."""
        recs = []

        if features.avg_knee_angle < 80:
            recs.append("Try extending your knees slightly for more power")
        elif features.avg_knee_angle > 130:
            recs.append("Bend your knees more for better push-off")

        if features.avg_hip_angle < 40:
            recs.append("Open your hip angle more")
        elif features.avg_hip_angle > 100:
            recs.append("Close your hip angle slightly")

        if features.trunk_angle < 10:
            recs.append("Lean forward more for better acceleration")
        elif features.trunk_angle > 50:
            recs.append("Reduce trunk forward lean")

        if not recs:
            recs.append("Your position looks good!")

        return recs

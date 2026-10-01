"""Biomechanical analysis of sprint start position."""

from __future__ import annotations

import numpy as np

from detection.entities import (
    BiomechanicalAngles,
    LandmarkIndex,
    PoseLandmarks,
    SprintMetrics,
)


class BiomechanicsAnalyzer:
    """Calculate biomechanical metrics from pose landmarks."""

    def __init__(self, visibility_threshold: float = 0.5):
        self.visibility_threshold = visibility_threshold

    def analyze(self, landmarks: PoseLandmarks) -> SprintMetrics:
        """Analyze sprint start position from landmarks."""
        angles = self._calculate_angles(landmarks)
        front_leg, _ = self.detect_front_rear_leg(landmarks)
        quality = self._calculate_quality(angles, front_leg)
        recommendations = self._generate_recommendations(angles, front_leg)

        return SprintMetrics(
            quality_score=quality,
            angles=angles,
        )

    def _get_landmark(
        self, landmarks: PoseLandmarks, index: LandmarkIndex
    ) -> np.ndarray | None:
        """Get landmark array by index, returns None if not available."""
        return landmarks.get_array(index)

    def _calculate_angles(self, landmarks: PoseLandmarks) -> BiomechanicalAngles:
        """Calculate all joint angles."""
        # BUG FIX 4: Use proper LandmarkIndex enum instead of fragile anonymous types
        nose = self._get_landmark(landmarks, LandmarkIndex.NOSE)
        ls = self._get_landmark(landmarks, LandmarkIndex.LEFT_SHOULDER)
        rs = self._get_landmark(landmarks, LandmarkIndex.RIGHT_SHOULDER)
        lh = self._get_landmark(landmarks, LandmarkIndex.LEFT_HIP)
        rh = self._get_landmark(landmarks, LandmarkIndex.RIGHT_HIP)
        lk = self._get_landmark(landmarks, LandmarkIndex.LEFT_KNEE)
        rk = self._get_landmark(landmarks, LandmarkIndex.RIGHT_KNEE)
        la = self._get_landmark(landmarks, LandmarkIndex.LEFT_ANKLE)
        ra = self._get_landmark(landmarks, LandmarkIndex.RIGHT_ANKLE)
        lf = self._get_landmark(landmarks, LandmarkIndex.LEFT_FOOT_INDEX)
        rf = self._get_landmark(landmarks, LandmarkIndex.RIGHT_FOOT_INDEX)

        mid_shoulder = (ls + rs) / 2 if ls is not None and rs is not None else None
        mid_hip = (lh + rh) / 2 if lh is not None and rh is not None else None

        return BiomechanicalAngles(
            left_knee=self._calc_angle(lh, lk, la),
            right_knee=self._calc_angle(rh, rk, ra),
            left_hip=self._calc_angle(ls, lh, lk),
            right_hip=self._calc_angle(rs, rh, rk),
            left_ankle=self._calc_angle(lk, la, lf),
            right_ankle=self._calc_angle(rk, ra, rf),
            trunk_angle=self._calc_trunk_angle(mid_shoulder, mid_hip),
        )

    def detect_front_rear_leg(self, landmarks: PoseLandmarks) -> tuple[str, str]:
        """Detect which leg is front/rear based on knee flexion.

        In sprint start "set" position, the front leg is more flexed (smaller knee angle).
        This method uses knee angle as primary indicator, with foot position as fallback.

        Returns (front_leg, rear_leg) as 'left' or 'right'.
        """
        # Get all required landmarks
        lh = self._get_landmark(landmarks, LandmarkIndex.LEFT_HIP)
        rh = self._get_landmark(landmarks, LandmarkIndex.RIGHT_HIP)
        lk = self._get_landmark(landmarks, LandmarkIndex.LEFT_KNEE)
        rk = self._get_landmark(landmarks, LandmarkIndex.RIGHT_KNEE)
        la = self._get_landmark(landmarks, LandmarkIndex.LEFT_ANKLE)
        ra = self._get_landmark(landmarks, LandmarkIndex.RIGHT_ANKLE)

        # Calculate knee angles
        left_knee_angle = self._calc_angle(lh, lk, la)
        right_knee_angle = self._calc_angle(rh, rk, ra)

        # Primary method: front leg has more flexion (smaller angle)
        # In sprint start, front knee is typically 80-100°, rear is 110-150°
        if (
            left_knee_angle is not None
            and right_knee_angle is not None
            and left_knee_angle > 0
            and right_knee_angle > 0
        ):
            if left_knee_angle < right_knee_angle:
                return ("left", "right")  # Left is front (more flexed)
            else:
                return ("right", "left")  # Right is front (more flexed)

        # Fallback: use foot position (x-coordinate)
        lf = self._get_landmark(landmarks, LandmarkIndex.LEFT_FOOT_INDEX)
        rf = self._get_landmark(landmarks, LandmarkIndex.RIGHT_FOOT_INDEX)

        if lf is None or rf is None:
            lf = self._get_landmark(landmarks, LandmarkIndex.LEFT_ANKLE)
            rf = self._get_landmark(landmarks, LandmarkIndex.RIGHT_ANKLE)

        if lf is None or rf is None:
            return ("left", "right")  # Default fallback

        # In profile view, foot with smaller x-coordinate is typically front
        if lf[0] < rf[0]:
            return ("left", "right")
        else:
            return ("right", "left")

    def _calc_angle(self, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float | None:
        """Calculate angle at point b (in degrees). Returns None if landmarks are missing."""
        if any(p is None for p in [a, b, c]):
            return None

        ba = a[:3] - b[:3]
        bc = c[:3] - b[:3]

        dot = np.dot(ba, bc)
        mag_ba = np.linalg.norm(ba)
        mag_bc = np.linalg.norm(bc)

        if mag_ba == 0 or mag_bc == 0:
            return 0.0

        cos_angle = np.clip(dot / (mag_ba * mag_bc), -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_angle)))

    def _calc_trunk_angle(self, shoulder: np.ndarray, hip: np.ndarray) -> float:
        """Calculate trunk inclination angle from horizontal.

        BUG FIX: Removed unused nose parameter. Uses 2D projection (x,y) instead of 3D.
        Returns angle in degrees from horizontal (0° = vertical, 90° = horizontal).
        Optimal range for sprint start: 15-45° from horizontal.
        Clamped to 0-90° to prevent invalid angles.
        """
        if shoulder is None or hip is None:
            return 0.0

        # Use 2D projection (x, y) - ignore Z for profile view
        trunk_vector = shoulder[:2] - hip[:2]  # Only x, y

        # Check minimum distance between shoulder and hip (avoid degenerate cases)
        trunk_length = np.linalg.norm(trunk_vector)
        if trunk_length < 0.01:  # Too close, invalid measurement
            return 0.0

        # Vertical vector pointing up in image coordinates
        vertical = np.array([0, -1])  # y-axis points down in images

        # Calculate angle from vertical
        cos_angle = np.dot(trunk_vector, vertical) / (trunk_length + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle_from_vertical = float(np.degrees(np.arccos(cos_angle)))

        # Convert to angle from horizontal (90 - angle_from_vertical)
        angle_from_horizontal = 90.0 - angle_from_vertical

        # Clamp to valid range (0-90°) - negative angles don't make sense for sprint start
        return max(0.0, min(90.0, angle_from_horizontal))

    def _calculate_quality(
        self, angles: BiomechanicalAngles, front_leg: str = "left"
    ) -> float:
        """Calculate position quality score (0-100) using literature-based ranges.

        Reference ranges (from literature):
        - Front knee: 80-100° (Coh et al. 2017, Debaere et al. 2013)
        - Rear knee: 110-150° (Coh et al. 2017)
        - Front hip: 45-70° (Coh et al. 2017, Vanrenterghem et al. 2017)
        - Rear hip: 85-115° (Coh et al. 2017)
        - Trunk: 15-45° from horizontal (Harland & Steele 1997, Mero et al. 1992)
        """
        scores = []

        front_knee = angles.left_knee if front_leg == "left" else angles.right_knee
        rear_knee = angles.right_knee if front_leg == "left" else angles.left_knee
        front_hip = angles.left_hip if front_leg == "left" else angles.right_hip
        rear_hip = angles.right_hip if front_leg == "left" else angles.left_hip

        # Front knee: optimal 80-100°
        if 80 <= front_knee <= 100:
            scores.append(100)
        elif 60 <= front_knee < 80 or 100 < front_knee <= 120:
            scores.append(70)
        elif 45 <= front_knee < 60 or 120 < front_knee <= 140:
            scores.append(40)
        else:
            scores.append(20)

        # Rear knee: optimal 110-150°
        if 110 <= rear_knee <= 150:
            scores.append(100)
        elif 90 <= rear_knee < 110 or 150 < rear_knee <= 170:
            scores.append(70)
        elif 70 <= rear_knee < 90 or 170 < rear_knee:
            scores.append(40)
        else:
            scores.append(20)

        # Front hip: optimal 45-70°
        if 45 <= front_hip <= 70:
            scores.append(100)
        elif 30 <= front_hip < 45 or 70 < front_hip <= 90:
            scores.append(70)
        elif 15 <= front_hip < 30 or 90 < front_hip <= 110:
            scores.append(40)
        else:
            scores.append(20)

        # Rear hip: optimal 85-115°
        if 85 <= rear_hip <= 115:
            scores.append(100)
        elif 70 <= rear_hip < 85 or 115 < rear_hip <= 130:
            scores.append(70)
        elif 50 <= rear_hip < 70 or 130 < rear_hip <= 150:
            scores.append(40)
        else:
            scores.append(20)

        # Trunk angle: optimal 15-45° from horizontal
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

    def _generate_recommendations(
        self, angles: BiomechanicalAngles, front_leg: str = "left"
    ) -> list[str]:
        """Generate recommendations based on angles and front/rear leg detection."""
        recs = []

        front_knee = angles.left_knee if front_leg == "left" else angles.right_knee
        rear_knee = angles.right_knee if front_leg == "left" else angles.left_knee
        front_hip = angles.left_hip if front_leg == "left" else angles.right_hip
        rear_hip = angles.right_hip if front_leg == "left" else angles.left_hip

        # Front knee recommendations
        if front_knee < 70:
            recs.append(
                "Rodilla delantera muy flexionada. Extiende ligeramente para más potencia de empuje."
            )
        elif front_knee > 110:
            recs.append(
                "Rodilla delantera poco flexionada. Flexiona más para mejor impulso inicial."
            )

        # Rear knee recommendations
        if rear_knee < 100:
            recs.append(
                "Rodilla trasera muy flexionada. Extiende para mejor preparación del primer paso."
            )
        elif rear_knee > 160:
            recs.append(
                "Rodilla trasera demasiado extendida. Flexiona ligeramente para reacción más rápida."
            )

        # Front hip recommendations
        if front_hip < 40:
            recs.append(
                "Cadera delantera muy cerrada. Abre más el ángulo para mejor extensión."
            )
        elif front_hip > 80:
            recs.append(
                "Cadera delantera muy abierta. Cierra más para mantener centro de gravedad bajo."
            )

        # Rear hip recommendations
        if rear_hip < 75:
            recs.append(
                "Cadera trasera muy cerrada. Esto limita la longitud del primer paso."
            )
        elif rear_hip > 125:
            recs.append(
                "Cadera trasera muy abierta. Puede causar pérdida de estabilidad."
            )

        # Trunk recommendations
        trunk = angles.trunk_angle
        if trunk < 10:
            recs.append(
                "Tronco muy vertical. Inclínate más hacia adelante (óptimo: 15-45°)."
            )
        elif trunk > 50:
            recs.append(
                "Tronco muy inclinado. Endereza ligeramente para mejor equilibrio."
            )

        if not recs:
            recs.append("Posición dentro de los rangos óptimos según literatura.")

        return recs

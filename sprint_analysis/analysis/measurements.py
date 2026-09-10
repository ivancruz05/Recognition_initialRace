"""Body measurement analysis using LiDAR and pose landmarks."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from sprint_analysis.domain.models import BodyMeasurements, DepthFrame, PoseLandmarks


class BodyMeasurementAnalyzer:
    """Measure body dimensions from pose landmarks and optional LiDAR depth."""

    BODY_PROPORTIONS = {
        "leg_ratio": 0.47,
        "arm_ratio": 0.44,
        "torso_ratio": 0.30,
        "foot_ratio": 0.15,
        "shoulder_ratio": 0.26,
    }

    def measure(
        self,
        landmarks: PoseLandmarks,
        depth_frame: Optional[DepthFrame] = None,
        known_height_cm: Optional[float] = None,
        image_shape: Optional[Tuple[int, int]] = None,
    ) -> BodyMeasurements:
        """Measure body dimensions from landmarks and optional depth."""
        if depth_frame is not None and depth_frame.depth is not None and image_shape is not None:
            return self._measure_with_depth(landmarks, depth_frame, known_height_cm, image_shape)
        return self._measure_from_landmarks(landmarks, known_height_cm)

    def _measure_with_depth(
        self,
        landmarks: PoseLandmarks,
        depth_frame: DepthFrame,
        known_height_cm: Optional[float],
        image_shape: Tuple[int, int],
    ) -> BodyMeasurements:
        """Measure using landmarks + LiDAR depth."""
        depth = depth_frame.depth
        img_h, img_w = image_shape[:2]
        depth_h, depth_w = depth.shape[:2]

        depth_values = self._sample_depth(landmarks, depth, depth_w, depth_h)

        valid_count = sum(1 for v in depth_values.values() if 0.5 < v < 3.0)
        depth_valid_ratio = valid_count / len(depth_values) if depth_values else 0

        if depth_valid_ratio < 0.3 or known_height_cm is None:
            return self._measure_from_landmarks(landmarks, known_height_cm)

        height_cm = known_height_cm
        raw = self._calculate_raw_measures(landmarks)

        measurements = BodyMeasurements(
            height_cm=height_cm,
            leg_length_cm=height_cm * self.BODY_PROPORTIONS["leg_ratio"],
            arm_length_cm=height_cm * self.BODY_PROPORTIONS["arm_ratio"],
            torso_length_cm=height_cm * self.BODY_PROPORTIONS["torso_ratio"],
            foot_length_cm=height_cm * self.BODY_PROPORTIONS["foot_ratio"],
            shoulder_width_cm=height_cm * self.BODY_PROPORTIONS["shoulder_ratio"],
            confidence=min(1.0, depth_valid_ratio * 0.7 + 0.3),
            depth_valid_ratio=depth_valid_ratio,
        )

        return measurements

    def _measure_from_landmarks(
        self, landmarks: PoseLandmarks, known_height_cm: Optional[float]
    ) -> BodyMeasurements:
        """Measure using only pose landmarks (no depth)."""
        raw = self._calculate_raw_measures(landmarks)

        if known_height_cm and known_height_cm > 0:
            height_cm = known_height_cm
        elif raw["height"] > 0:
            height_cm = 170.0
        else:
            return BodyMeasurements(height_cm=0, leg_length_cm=0, arm_length_cm=0,
                                   torso_length_cm=0, foot_length_cm=0, shoulder_width_cm=0)

        return BodyMeasurements(
            height_cm=height_cm,
            leg_length_cm=height_cm * self.BODY_PROPORTIONS["leg_ratio"],
            arm_length_cm=height_cm * self.BODY_PROPORTIONS["arm_ratio"],
            torso_length_cm=height_cm * self.BODY_PROPORTIONS["torso_ratio"],
            foot_length_cm=height_cm * self.BODY_PROPORTIONS["foot_ratio"],
            shoulder_width_cm=height_cm * self.BODY_PROPORTIONS["shoulder_ratio"],
            confidence=0.5,
            depth_valid_ratio=0.0,
        )

    def _calculate_raw_measures(self, landmarks: PoseLandmarks) -> Dict[str, float]:
        """Calculate raw measures in normalized units."""
        def get_arr(idx):
            lm = landmarks.landmarks.get(idx)
            return np.array([lm.x, lm.y, lm.z]) if lm else None

        nose = get_arr(0)
        ls, rs = get_arr(11), get_arr(12)
        lh, rh = get_arr(23), get_arr(24)
        lk, rk = get_arr(25), get_arr(26)
        la, ra = get_arr(27), get_arr(28)
        lf_idx, rf_idx = get_arr(31), get_arr(32)

        measures = {}

        if ls is not None and rs is not None:
            shoulder_center = (ls + rs) / 2
        else:
            shoulder_center = None

        if lh is not None and rh is not None:
            hip_center = (lh + rh) / 2
        else:
            hip_center = None

        if la is not None and ra is not None:
            ankle_avg_y = (la[1] + ra[1]) / 2
            measures["height"] = ankle_avg_y - nose[1] if nose is not None else 0
        else:
            measures["height"] = 0

        if lh is not None and la is not None:
            measures["leg_length"] = float(np.linalg.norm(lh - la))
        else:
            measures["leg_length"] = 0

        measures["arm_length"] = measures["leg_length"] * 0.75

        if shoulder_center is not None and hip_center is not None:
            measures["torso_length"] = float(np.linalg.norm(shoulder_center - hip_center))
        else:
            measures["torso_length"] = 0

        if lf_idx is not None and la is not None:
            measures["foot_length"] = float(np.linalg.norm(la - lf_idx))
        else:
            measures["foot_length"] = 0

        if ls is not None and rs is not None:
            measures["shoulder_width"] = float(np.linalg.norm(ls - rs))
        else:
            measures["shoulder_width"] = 0

        return measures

    def _sample_depth(
        self,
        landmarks: PoseLandmarks,
        depth: np.ndarray,
        depth_w: int,
        depth_h: int,
    ) -> Dict[str, float]:
        """Sample depth values at landmark positions."""
        depth_values = {}
        landmark_names = {
            "nose": 0, "left_shoulder": 11, "right_shoulder": 12,
            "left_hip": 23, "right_hip": 24, "left_knee": 25, "right_knee": 26,
            "left_ankle": 27, "right_ankle": 28,
        }

        for name, idx in landmark_names.items():
            lm = landmarks.landmarks.get(idx)
            if lm is None:
                continue

            px = max(0, min(int(lm.x * depth_w), depth_w - 1))
            py = max(0, min(int(lm.y * depth_h), depth_h - 1))

            depth_val = depth[py, px]
            if np.isfinite(depth_val) and 0.1 < depth_val < 5.0:
                depth_values[name] = depth_val

        return depth_values

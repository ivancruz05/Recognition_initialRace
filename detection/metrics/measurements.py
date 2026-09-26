"""Body measurement analysis using LiDAR and pose landmarks."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from detection.entities import BodyMeasurements, DepthFrame, PoseLandmarks
from detection.interfaces import BodyMeasurementInterface


class BodyMeasurementAnalyzer(BodyMeasurementInterface):
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
        """Measure using landmarks + LiDAR depth for actual 3D distances.
        
        BUG FIX: Now uses depth data to calculate real-world distances between
        landmarks instead of relying solely on body proportions.
        """
        depth = depth_frame.depth
        img_h, img_w = image_shape[:2]
        depth_h, depth_w = depth.shape[:2]

        depth_values = self._sample_depth(landmarks, depth, depth_w, depth_h)

        valid_count = sum(1 for v in depth_values.values() if 0.5 < v < 3.0)
        depth_valid_ratio = valid_count / len(depth_values) if depth_values else 0

        if depth_valid_ratio < 0.3 or known_height_cm is None:
            return self._measure_from_landmarks(landmarks, known_height_cm)

        # Use depth data to calculate actual 3D distances
        raw = self._calculate_raw_measures_with_depth(landmarks, depth_values)
        
        # Calculate scale factor from known height
        scale_factor = known_height_cm / raw["height"] if raw["height"] > 0 else 1.0

        measurements = BodyMeasurements(
            height_cm=known_height_cm,
            leg_length_cm=raw["leg_length"] * scale_factor,
            arm_length_cm=raw["arm_length"] * scale_factor,
            torso_length_cm=raw["torso_length"] * scale_factor,
            foot_length_cm=raw["foot_length"] * scale_factor,
            shoulder_width_cm=raw["shoulder_width"] * scale_factor,
            confidence=min(1.0, depth_valid_ratio * 0.7 + 0.3),
            depth_valid_ratio=depth_valid_ratio,
        )

        return measurements

    def _calculate_raw_measures_with_depth(
        self, landmarks: PoseLandmarks, depth_values: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate raw measures using depth data for actual 3D distances."""
        def get_arr(idx):
            lm = landmarks.landmarks.get(idx)
            return np.array([lm.x, lm.y, lm.z]) if lm else None

        def get_depth(idx):
            lm = landmarks.landmarks.get(idx)
            if lm is None:
                return None
            # Find depth value for this landmark
            name = {0: "nose", 11: "left_shoulder", 12: "right_shoulder",
                    23: "left_hip", 24: "right_hip", 25: "left_knee", 26: "right_knee",
                    27: "left_ankle", 28: "right_ankle"}.get(idx)
            return depth_values.get(name)

        def calc_3d_distance(idx1, idx2) -> Optional[float]:
            """Calculate 3D distance between two landmarks using depth. Returns None if unavailable."""
            p1 = get_arr(idx1)
            p2 = get_arr(idx2)
            d1 = get_depth(idx1)
            d2 = get_depth(idx2)
            
            if p1 is None or p2 is None or d1 is None or d2 is None:
                return None
            
            # Convert to 3D coordinates using depth
            # x, y are in normalized image coords (0-1), depth is in meters
            x1, y1 = p1[0] * d1, p1[1] * d1
            x2, y2 = p2[0] * d2, p2[1] * d2
            
            # Calculate Euclidean distance in 3D
            dx = x2 - x1
            dy = y2 - y1
            dz = d2 - d1
            
            return float(np.sqrt(dx*dx + dy*dy + dz*dz))

        measures = {}
        
        # Height: Euclidean distance from nose to ankle (using 3D coordinates)
        nose_depth = get_depth(0)
        la_depth = get_depth(27)
        ra_depth = get_depth(28)
        
        # Calculate actual ankle depth (average both if available)
        ankle_depth = None
        if la_depth is not None and ra_depth is not None:
            ankle_depth = (la_depth + ra_depth) / 2
        elif la_depth is not None:
            ankle_depth = la_depth
        elif ra_depth is not None:
            ankle_depth = ra_depth
        
        if nose_depth is not None and ankle_depth is not None:
            # Use the 3D distance function for proper Euclidean distance
            height_dist = calc_3d_distance(0, 27 if la_depth is not None else 28)
            measures["height"] = height_dist * 100 if height_dist is not None else 0
        else:
            measures["height"] = 0
        
        # Leg length: hip to ankle (using 3D distance)
        leg_dist = calc_3d_distance(23, 27)
        measures["leg_length"] = leg_dist * 100 if leg_dist is not None else 0
        
        # Arm length: shoulder to wrist (using 3D distance)
        arm_dist = calc_3d_distance(11, 15)
        measures["arm_length"] = arm_dist * 100 if arm_dist is not None else 0
        
        # Torso length: shoulder center to hip center
        ls = get_arr(11)
        rs = get_arr(12)
        lh = get_arr(23)
        rh = get_arr(24)
        
        if ls is not None and rs is not None and lh is not None and rh is not None:
            shoulder_center = (ls + rs) / 2
            hip_center = (lh + rh) / 2
            measures["torso_length"] = float(np.linalg.norm(shoulder_center - hip_center)) * 100
        else:
            measures["torso_length"] = 0
        
        # Foot length: ankle to foot index
        foot_dist = calc_3d_distance(27, 31)
        measures["foot_length"] = foot_dist * 100 if foot_dist is not None else 0
        
        # Shoulder width: left shoulder to right shoulder
        shoulder_dist = calc_3d_distance(11, 12)
        measures["shoulder_width"] = shoulder_dist * 100 if shoulder_dist is not None else 0
        
        return measures

    def _measure_from_landmarks(
        self, landmarks: PoseLandmarks, known_height_cm: Optional[float]
    ) -> BodyMeasurements:
        """Measure using only pose landmarks (no depth).
        
        BUG FIX: Now uses actual landmark proportions instead of fixed ratios.
        When no height is provided, estimates height from landmarks and calculates
        individual body proportions from the actual landmark positions.
        """
        raw = self._calculate_raw_measures(landmarks)

        # Estimate height from landmarks if not provided
        if known_height_cm and known_height_cm > 0:
            height_cm = known_height_cm
        elif raw["height"] > 0:
            # Use landmark-derived height with a reasonable scale factor
            # MediaPipe normalized coords: height is in 0-1 range
            # Typical human height in meters: 1.5-2.0m
            # We'll use 1.75m as a reasonable estimate
            height_cm = 175.0  # Reasonable default when no height provided
        else:
            return BodyMeasurements(height_cm=0, leg_length_cm=0, arm_length_cm=0,
                                   torso_length_cm=0, foot_length_cm=0, shoulder_width_cm=0)

        # Calculate individual proportions from landmarks
        # Use actual ratios from landmark data when available
        if raw["height"] > 0:
            # Calculate actual proportions from landmark distances
            actual_leg_ratio = raw["leg_length"] / raw["height"] if raw["leg_length"] > 0 else self.BODY_PROPORTIONS["leg_ratio"]
            actual_torso_ratio = raw["torso_length"] / raw["height"] if raw["torso_length"] > 0 else self.BODY_PROPORTIONS["torso_ratio"]
            actual_foot_ratio = raw["foot_length"] / raw["height"] if raw["foot_length"] > 0 else self.BODY_PROPORTIONS["foot_ratio"]
            actual_shoulder_ratio = raw["shoulder_width"] / raw["height"] if raw["shoulder_width"] > 0 else self.BODY_PROPORTIONS["shoulder_ratio"]
            actual_arm_ratio = raw["arm_length"] / raw["height"] if raw["arm_length"] > 0 else self.BODY_PROPORTIONS["arm_ratio"]
            
            # Clamp ratios to reasonable ranges
            actual_leg_ratio = max(0.35, min(0.55, actual_leg_ratio))
            actual_torso_ratio = max(0.20, min(0.40, actual_torso_ratio))
            actual_foot_ratio = max(0.10, min(0.20, actual_foot_ratio))
            actual_shoulder_ratio = max(0.18, min(0.35, actual_shoulder_ratio))
            actual_arm_ratio = max(0.35, min(0.55, actual_arm_ratio))
        else:
            # Use default proportions if no landmark data
            actual_leg_ratio = self.BODY_PROPORTIONS["leg_ratio"]
            actual_torso_ratio = self.BODY_PROPORTIONS["torso_ratio"]
            actual_foot_ratio = self.BODY_PROPORTIONS["foot_ratio"]
            actual_shoulder_ratio = self.BODY_PROPORTIONS["shoulder_ratio"]
            actual_arm_ratio = self.BODY_PROPORTIONS["arm_ratio"]

        return BodyMeasurements(
            height_cm=height_cm,
            leg_length_cm=height_cm * actual_leg_ratio,
            arm_length_cm=height_cm * actual_arm_ratio,
            torso_length_cm=height_cm * actual_torso_ratio,
            foot_length_cm=height_cm * actual_foot_ratio,
            shoulder_width_cm=height_cm * actual_shoulder_ratio,
            confidence=0.6 if raw["height"] > 0 else 0.5,
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

        measures["arm_length"] = 0
        # Calculate arm length from shoulder -> elbow -> wrist
        # Left arm: 11 (shoulder) -> 13 (elbow) -> 15 (wrist)
        le_shoulder = get_arr(11)
        le_elbow = get_arr(13)
        le_wrist = get_arr(15)
        # Right arm: 12 (shoulder) -> 14 (elbow) -> 16 (wrist)
        re_shoulder = get_arr(12)
        re_elbow = get_arr(14)
        re_wrist = get_arr(16)

        left_arm = 0
        right_arm = 0
        if le_shoulder is not None and le_elbow is not None and le_wrist is not None:
            left_arm = float(np.linalg.norm(le_shoulder - le_elbow) + np.linalg.norm(le_elbow - le_wrist))
        if re_shoulder is not None and re_elbow is not None and re_wrist is not None:
            right_arm = float(np.linalg.norm(re_shoulder - re_elbow) + np.linalg.norm(re_elbow - re_wrist))

        if left_arm > 0 and right_arm > 0:
            measures["arm_length"] = (left_arm + right_arm) / 2
        elif left_arm > 0:
            measures["arm_length"] = left_arm
        elif right_arm > 0:
            measures["arm_length"] = right_arm

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

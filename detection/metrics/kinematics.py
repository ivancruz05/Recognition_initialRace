"""Kinematic analysis: velocity, stride length and cadence from pose tracks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from detection.entities import KinematicsResult, LandmarkIndex, PoseLandmarks
from detection.interfaces import PixelToWorldTransform


@dataclass
class FootContact:
    """A detected foot-contact event."""
    frame_idx: int
    leg: str  # "left" or "right"
    time_s: float
    position_m: Tuple[float, float]


class KinematicsAnalyzer:
    """Compute sprint kinematics from a time-series of pose landmarks."""

    def __init__(
        self,
        calibration: PixelToWorldTransform,
        visibility_threshold: float = 0.5,
        smoothing_window: int = 7,
    ):
        self.calibration = calibration
        self.visibility_threshold = visibility_threshold
        self.smoothing_window = smoothing_window

    def analyze(
        self,
        landmarks_sequence: List[PoseLandmarks],
        timestamps: List[float],
        frame_shape: Tuple[int, int],
    ) -> KinematicsResult:
        """Analyze a sprint sequence and return kinematic variables."""
        if len(landmarks_sequence) != len(timestamps):
            raise ValueError("landmarks_sequence and timestamps must have the same length")
        if len(landmarks_sequence) < 3:
            return KinematicsResult()

        # 1. Hip centre trajectory in world coordinates.
        hip_positions_px = np.array([
            self._hip_center_px(lm, frame_shape) for lm in landmarks_sequence
        ])
        valid = ~np.isnan(hip_positions_px).any(axis=1)
        if valid.sum() < 3:
            return KinematicsResult()

        hip_positions_m = self.calibration.image_to_world(hip_positions_px[valid])
        valid_times = np.array(timestamps)[valid]

        # 2. Smooth trajectory.
        smoothed = self._smooth(hip_positions_m, valid_times)

        # 3. Velocity.
        velocity = self._compute_velocity(smoothed, valid_times)

        # 4. Foot contacts and stride metrics.
        contacts = self._detect_contacts(landmarks_sequence, timestamps, frame_shape)
        stride_lengths, step_durations = self._stride_metrics(contacts)

        total_distance = float(
            np.sum(np.linalg.norm(np.diff(smoothed, axis=0), axis=1))
        )
        total_time = float(valid_times[-1] - valid_times[0]) if len(valid_times) > 1 else 0.0

        cadence = 0.0
        if total_time > 0 and contacts:
            cadence = len(contacts) / total_time

        return KinematicsResult(
            timestamps=valid_times.tolist(),
            hip_positions_m=[tuple(p) for p in smoothed.tolist()],
            velocity_ms=velocity.tolist(),
            stride_length_m=stride_lengths,
            cadence_steps_per_s=[cadence] * len(valid_times) if cadence else [],
            max_velocity_ms=float(np.max(velocity)) if len(velocity) else 0.0,
            average_velocity_ms=float(total_distance / total_time) if total_time > 0 else 0.0,
            total_distance_m=total_distance,
        )

    @staticmethod
    def _hip_center_px(
        landmarks: PoseLandmarks,
        frame_shape: Tuple[int, int],
    ) -> Tuple[float, float]:
        """Hip centre in pixel coordinates."""
        h, w = frame_shape[:2]
        left = landmarks.get_array(LandmarkIndex.LEFT_HIP)
        right = landmarks.get_array(LandmarkIndex.RIGHT_HIP)
        if left is not None and right is not None:
            return ((left[0] + right[0]) / 2 * w, (left[1] + right[1]) / 2 * h)
        if left is not None:
            return (left[0] * w, left[1] * h)
        if right is not None:
            return (right[0] * w, right[1] * h)
        return (np.nan, np.nan)

    def _smooth(
        self,
        positions: np.ndarray,
        times: np.ndarray,
    ) -> np.ndarray:
        """Smooth a 2D trajectory using Savitzky-Golay if enough points."""
        try:
            from scipy.signal import savgol_filter
        except ImportError:
            return positions

        n = len(positions)
        window = min(self.smoothing_window, n)
        if window % 2 == 0:
            window -= 1
        if window < 5:
            return positions

        # Resample to uniform time grid for the filter.
        uniform_t = np.linspace(times[0], times[-1], n)
        uniform_x = np.interp(uniform_t, times, positions[:, 0])
        uniform_y = np.interp(uniform_t, times, positions[:, 1])

        polyorder = min(3, window - 1)
        sx = savgol_filter(uniform_x, window, polyorder)
        sy = savgol_filter(uniform_y, window, polyorder)
        return np.column_stack([sx, sy])

    @staticmethod
    def _compute_velocity(positions: np.ndarray, times: np.ndarray) -> np.ndarray:
        """Instantaneous speed from a 2D trajectory."""
        if len(positions) < 2:
            return np.array([])
        deltas = np.linalg.norm(np.diff(positions, axis=0), axis=1)
        dt = np.diff(times)
        speed = np.zeros(len(positions))
        with np.errstate(divide="ignore", invalid="ignore"):
            mid = deltas / dt
        speed[1:] = mid
        speed[:-1] = (speed[:-1] + mid) / 2
        speed = np.nan_to_num(speed, nan=0.0, posinf=0.0, neginf=0.0)
        return speed

    def _detect_contacts(
        self,
        landmarks_sequence: List[PoseLandmarks],
        timestamps: List[float],
        frame_shape: Tuple[int, int],
    ) -> List[FootContact]:
        """Detect foot-contact events from foot-index vertical trajectories."""
        try:
            from scipy.signal import find_peaks
        except ImportError:
            return []

        contacts: List[FootContact] = []
        h, w = frame_shape[:2]

        for leg, foot_index in (("left", 31), ("right", 32)):
            ys = []
            xs = []
            valid_idx = []
            for i, lm in enumerate(landmarks_sequence):
                point = lm.landmarks.get(foot_index)
                if point is None or point.visibility < self.visibility_threshold:
                    continue
                ys.append(point.y * h)
                xs.append(point.x * w)
                valid_idx.append(i)

            if len(ys) < 5:
                continue

            ys_arr = np.array(ys, dtype=float)
            # Contact is the lowest point in the image (largest y).
            peaks, _ = find_peaks(
                ys_arr,
                prominence=np.std(ys_arr) * 0.3,
                distance=max(3, int(len(ys_arr) * 0.08)),
            )

            for p in peaks:
                frame_i = valid_idx[p]
                pos_px = np.array([[xs[p], ys[p]]], dtype=np.float32)
                pos_m = self.calibration.image_to_world(pos_px)[0]
                contacts.append(FootContact(
                    frame_idx=frame_i,
                    leg=leg,
                    time_s=timestamps[frame_i],
                    position_m=tuple(pos_m.tolist()),
                ))

        contacts.sort(key=lambda c: c.time_s)
        return contacts

    @staticmethod
    def _stride_metrics(contacts: List[FootContact]) -> Tuple[List[float], List[float]]:
        """Return stride lengths and step durations from foot contacts."""
        if len(contacts) < 2:
            return [], []

        stride_lengths: List[float] = []
        step_durations: List[float] = []

        # Step length = distance along track (x) between consecutive contacts.
        for prev, cur in zip(contacts[:-1], contacts[1:]):
            step_durations.append(cur.time_s - prev.time_s)
            stride_lengths.append(abs(cur.position_m[0] - prev.position_m[0]))

        return stride_lengths, step_durations

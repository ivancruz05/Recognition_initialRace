"""Tests for kinematic analysis."""

import numpy as np
import pytest

from drone_analysis.analysis.kinematics import KinematicsAnalyzer
from drone_analysis.domain.models import Landmark3D, PoseLandmarks
from drone_analysis.infrastructure.calibration.aruco import ArUcoCalibration


def _landmarks(
    hip_x: float,
    hip_y: float,
    left_foot_y: float,
    right_foot_y: float,
) -> PoseLandmarks:
    """Build a minimal PoseLandmarks dict for kinematics."""
    return PoseLandmarks(landmarks={
        23: Landmark3D(x=hip_x - 0.02, y=hip_y, z=0.0, visibility=1.0),  # left hip
        24: Landmark3D(x=hip_x + 0.02, y=hip_y, z=0.0, visibility=1.0),  # right hip
        31: Landmark3D(x=hip_x - 0.02, y=left_foot_y, z=0.0, visibility=1.0),  # left foot
        32: Landmark3D(x=hip_x + 0.02, y=right_foot_y, z=0.0, visibility=1.0),  # right foot
    })


def _make_calibration():
    cal = ArUcoCalibration(marker_config={})
    # image -> world: 640 px -> 10 m in x, 480 px -> 1 m in y
    H = np.array([[10.0 / 640.0, 0.0, 0.0], [0.0, 1.0 / 480.0, 0.0], [0.0, 0.0, 1.0]])
    cal.homography = H
    cal.homography_inv = np.linalg.inv(H)
    return cal


def test_kinematics_linear_sprint():
    cal = _make_calibration()
    analyzer = KinematicsAnalyzer(calibration=cal)

    n_frames = 61
    fps = 30.0
    timestamps = [i / fps for i in range(n_frames)]
    landmarks = []
    for i in range(n_frames):
        hip_x = i / (n_frames - 1)  # 0 -> 1 normalized
        # Alternate foot contacts every ~0.25 s (7-8 frames).
        phase = (i % 15) / 15.0
        left_contact = phase < 0.3
        right_contact = 0.5 <= phase < 0.8
        left_y = 0.9 if left_contact else 0.75
        right_y = 0.9 if right_contact else 0.75
        landmarks.append(_landmarks(hip_x, 0.5, left_y, right_y))

    result = analyzer.analyze(landmarks, timestamps, frame_shape=(480, 640))

    assert result.total_distance_m == pytest.approx(10.0, rel=0.1)
    assert result.average_velocity_ms == pytest.approx(5.0, rel=0.2)
    assert result.max_velocity_ms > 0
    assert len(result.velocity_ms) == n_frames
    assert len(result.cadence_steps_per_s) == n_frames
    assert result.cadence_steps_per_s[0] > 0
    assert len(result.stride_length_m) > 0

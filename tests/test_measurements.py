"""Tests de mediciones: distancias, escala y ángulos corporales."""

import numpy as np
import pytest

from drone_analysis.infrastructure.pose.geometry import (
    angle_at,
    estimate_all_distances,
    estimate_joint_angles,
    estimate_scale,
)


def _full_body(view=None, width=100, height=100):
    """Landmarks (33, 4) con la parte superior e inferior visibles."""
    landmarks = np.zeros((33, 4))
    view = view or [
        11, 12, 13, 14, 15, 16,
        23, 24, 25, 26, 27, 28,
    ]
    for idx in view:
        landmarks[idx, 3] = 1.0
    return landmarks


def test_angle_at_basic():
    assert angle_at((0, 1), (0, 0), (1, 0)) == pytest.approx(90.0)
    assert angle_at((-1, 0), (0, 0), (1, 0)) == pytest.approx(180.0, abs=0.1)
    assert angle_at((1, 1), (0, 0), (2, 2)) == pytest.approx(0.0, abs=0.1)


def test_estimate_scale_none_when_not_visible():
    landmarks = np.zeros((33, 4))
    assert estimate_scale(landmarks, 100, 100, "shoulder_width") is None


def test_estimate_all_distances_uses_shoulder_reference():
    landmarks = _full_body()
    landmarks[11] = [0.3, 0.5, 0.0, 1.0]
    landmarks[12] = [0.7, 0.5, 0.0, 1.0]
    landmarks[23] = [0.4, 0.6, 0.0, 1.0]
    landmarks[24] = [0.6, 0.6, 0.0, 1.0]

    distances, used_reference = estimate_all_distances(landmarks, 100, 100)
    assert used_reference == "shoulder_width"
    assert distances["shoulder_width"] == 0.40


def test_estimate_joint_angles_knee_ninety():
    landmarks = np.zeros((33, 4))
    landmarks[11] = [0.4, 0.3, 0.0, 1.0]
    landmarks[23] = [0.4, 0.5, 0.0, 1.0]
    landmarks[25] = [0.4, 0.75, 0.0, 1.0]
    landmarks[27] = [0.6, 0.75, 0.0, 1.0]

    angles = estimate_joint_angles(landmarks)
    assert abs(angles["left_knee"] - 90.0) < 1.0


def test_estimate_joint_angles_skip_invisible_parts():
    landmarks = np.zeros((33, 4))
    landmarks[11][3] = 1.0
    landmarks[12][3] = 1.0

    angles = estimate_joint_angles(landmarks)
    assert angles == {}

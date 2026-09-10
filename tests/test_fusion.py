"""Tests de la fusión de landmarks con depth map."""

import numpy as np

from src.fusion import SensorFusion
from src.synthetic import generate_depth_map, synthetic_landmarks_array


def _make_fusion():
    return SensorFusion(
        camera_intrinsics={"fx": 200.0, "fy": 200.0, "cx": 128.0, "cy": 96.0}
    )


def test_fusion_returns_3d_positions():
    landmarks = synthetic_landmarks_array()
    depth_map = generate_depth_map(256, 192)

    result = _make_fusion().fuse(landmarks, depth_map, 640, 480)

    assert result["positions_3d"].shape == (33, 3)
    assert result["visibility"].shape == (33,)

    valid = ~np.isnan(result["positions_3d"][:, 0])
    assert valid.sum() > 0


def test_fusion_distance_between_shoulders():
    landmarks = synthetic_landmarks_array()
    depth_map = generate_depth_map(256, 192)

    fusion = _make_fusion()
    result = fusion.fuse(landmarks, depth_map, 640, 480)
    positions = result["positions_3d"]

    distance = fusion.get_distance_between_points(positions, 11, 12)
    assert not np.isnan(distance)
    assert distance > 0
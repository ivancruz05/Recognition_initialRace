"""Tests de generación de datos sintéticos."""

import numpy as np

from src.synthetic import (
    generate_depth_map,
    generate_skeleton_image,
    generate_synthetic_frame,
    synthetic_landmarks_array,
)


def test_synthetic_landmarks_shape_and_visibility():
    landmarks = synthetic_landmarks_array()
    assert landmarks.shape == (33, 4)
    assert landmarks[11, 3] == 1.0
    assert landmarks[1, 3] == 1.0


def test_generate_synthetic_frame_shapes():
    rgb, depth = generate_synthetic_frame(width=320, height=240, depth_width=64, depth_height=48)
    assert rgb.shape == (240, 320, 3)
    assert depth.shape == (48, 64)
    assert depth.min() > 0


def test_generate_skeleton_image():
    img = generate_skeleton_image(640, 480)
    assert img.shape == (480, 640, 3)


def test_generate_depth_map_values():
    depth = generate_depth_map(256, 192, base_depth=2.0)
    assert np.all(depth > 0)
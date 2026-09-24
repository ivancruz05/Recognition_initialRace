"""Tests for ArUco calibration."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from drone_analysis.infrastructure.calibration.aruco import (
    ArUcoCalibration,
    CalibrationError,
    default_track_marker_config,
)


def test_default_marker_config():
    config = default_track_marker_config()
    assert config[0] == pytest.approx((0.0, 0.0))
    assert config[1] == pytest.approx((1.22, 0.0))
    assert config[2] == pytest.approx((0.0, 10.0))
    assert config[3] == pytest.approx((1.22, 10.0))


def test_calibration_not_calibrated_raises():
    cal = ArUcoCalibration(marker_config=default_track_marker_config())
    assert not cal.is_calibrated()
    with pytest.raises(CalibrationError):
        cal.image_to_world(np.array([[100, 100]]))


def test_calibration_save_load_roundtrip():
    cal = ArUcoCalibration(marker_config=default_track_marker_config())
    # Synthetic homography (image -> world): 50 px/m, origin offset (20, 10) px
    H = np.array([[0.02, 0.0, -0.4], [0.0, 0.02, -0.2], [0.0, 0.0, 1.0]])
    cal.homography = H
    cal.homography_inv = np.linalg.inv(H)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cal.json"
        cal.save(path)
        loaded = ArUcoCalibration.load(path)

    assert loaded.is_calibrated()
    np.testing.assert_allclose(loaded.homography, H)
    np.testing.assert_allclose(
        loaded.image_to_world(np.array([[70.0, 60.0]])),
        np.array([[1.0, 1.0]]),
        rtol=1e-5,
    )
    np.testing.assert_allclose(
        loaded.world_to_image(np.array([[1.0, 1.0]])),
        np.array([[70.0, 60.0]]),
        rtol=1e-5,
    )


def test_blank_image_does_not_calibrate():
    cal = ArUcoCalibration(marker_config=default_track_marker_config())
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    assert not cal.calibrate_from_image(blank)

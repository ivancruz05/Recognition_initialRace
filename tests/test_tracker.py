"""Tests for athlete tracking helpers."""

import numpy as np
import pytest

from drone_analysis.infrastructure.tracking.athlete_tracker import (
    AthleteTracker,
    crop_bbox,
)


def test_iou_perfect_overlap():
    tracker = AthleteTracker()
    assert tracker._iou((10, 10, 50, 50), (10, 10, 50, 50)) == pytest.approx(1.0)


def test_iou_no_overlap():
    tracker = AthleteTracker()
    assert tracker._iou((10, 10, 20, 20), (30, 30, 40, 40)) == pytest.approx(0.0)


def test_iou_partial_overlap():
    tracker = AthleteTracker()
    assert tracker._iou((0, 0, 10, 10), (5, 5, 15, 15)) == pytest.approx(25.0 / 175.0)


def test_crop_bbox_with_margin():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    crop, coords = crop_bbox(frame, (40, 40, 60, 60), margin=0.5)
    # 20x20 box + 50% margin => 40x40 crop
    assert crop.shape[0] == 40
    assert crop.shape[1] == 40
    assert coords == (30, 30, 70, 70)


def test_crop_bbox_clips_to_frame():
    frame = np.zeros((50, 50, 3), dtype=np.uint8)
    crop, coords = crop_bbox(frame, (0, 0, 10, 10), margin=1.0)
    assert coords[0] == 0
    assert coords[1] == 0
    assert coords[2] <= 50
    assert coords[3] <= 50

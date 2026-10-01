"""Tests for video stabilisation."""

import numpy as np

from detection.vision.stabilizer import VideoStabilizer


def test_stabilizer_compensates_translation():
    ref = np.zeros((200, 200, 3), dtype=np.uint8)
    ref[80:120, 80:120] = 255  # white square

    shifted = np.zeros((200, 200, 3), dtype=np.uint8)
    shifted[90:130, 90:130] = 255  # shifted by (10, 10)

    stabilizer = VideoStabilizer(ref_frame=ref, transform_type="similarity")
    corrected = stabilizer.stabilize(shifted)

    # The corrected frame should overlap strongly with the reference.
    overlap = np.sum((ref > 0) & (corrected > 0))
    ref_area = np.sum(ref > 0)
    assert overlap / ref_area > 0.7


def test_stabilizer_uses_first_frame_as_reference():
    ref = np.zeros((100, 100, 3), dtype=np.uint8)
    ref[40:60, 40:60] = 255

    stabilizer = VideoStabilizer()
    out = stabilizer.stabilize(ref)
    np.testing.assert_array_equal(out, ref)

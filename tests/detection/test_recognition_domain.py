"""Pure unit tests for the recognition domain; no adapters or I/O."""

import math

import pytest

from detection.domain.angle_calculation import (
    LEFT_ANKLE,
    LEFT_FOOT_INDEX,
    LEFT_HIP,
    LEFT_KNEE,
    LEFT_SHOULDER,
    RIGHT_HIP,
    RIGHT_ANKLE,
    RIGHT_KNEE,
    RIGHT_SHOULDER,
    calculate_angle_at,
    calculate_biomechanical_angles,
)
from detection.domain.landmarks import PoseLandmark2D, PoseLandmarkName
from detection.domain.entities import (
    BiomechanicalAngles,
    BiomechanicalFrameResult,
    CapturedFrame,
    RecognitionSession,
)
from detection.domain.exceptions import DomainInvariantError
from tests.detection.recognition_factories import (
    BiomechanicalFrameResultFactory,
    CapturedFrameFactory,
    RecognitionSessionFactory,
)


def _landmark(x, y, visibility=1.0):
    return PoseLandmark2D(x=x, y=y, visibility=visibility)


def test_value_objects_expose_validity_and_factory_defaults():
    result = BiomechanicalFrameResultFactory()

    assert result.session == RecognitionSessionFactory()
    assert result.frame_index == 0
    assert result.angles.left_knee_deg == 90.0
    assert result.pose_detected is True
    assert result.angles.validity["left_knee_deg"] is True
    assert result.angles.validity["right_knee_deg"] is False
    with pytest.raises(TypeError):
        result.angles.validity["left_knee_deg"] = False
    assert CapturedFrameFactory().payload is not None


def test_frame_result_copies_and_freezes_landmarks_mapping():
    landmarks = {PoseLandmarkName.LEFT_HIP: _landmark(0.2, 0.3)}
    result = BiomechanicalFrameResultFactory(landmarks=landmarks)

    landmarks[PoseLandmarkName.LEFT_KNEE] = _landmark(0.4, 0.5)

    assert list(result.landmarks) == [PoseLandmarkName.LEFT_HIP]
    with pytest.raises(TypeError):
        result.landmarks[PoseLandmarkName.LEFT_KNEE] = _landmark(0.4, 0.5)


@pytest.mark.parametrize(
    "angles,expected",
    [
        (BiomechanicalAngles(left_hip_deg=90, left_knee_deg=90, left_ankle_deg=90), True),
        (BiomechanicalAngles(right_hip_deg=90, right_knee_deg=90, right_ankle_deg=90), True),
        (BiomechanicalAngles(left_hip_deg=90, left_knee_deg=90), False),
        (BiomechanicalAngles(left_knee_deg=90, right_hip_deg=90, right_ankle_deg=90), False),
        (BiomechanicalAngles(), False),
    ],
)
def test_pose_ready_requires_complete_chain_on_either_side_without_view_inference(
    angles, expected
):
    result = BiomechanicalFrameResultFactory(angles=angles)

    assert result.pose_ready is expected


@pytest.mark.parametrize(
    "landmarks",
    [
        {"left_hip": _landmark(0.1, 0.1)},
        {PoseLandmarkName.LEFT_HIP: object()},
    ],
)
def test_frame_result_rejects_non_domain_landmark_mapping_entries(landmarks):
    with pytest.raises(DomainInvariantError):
        BiomechanicalFrameResultFactory(landmarks=landmarks)


@pytest.mark.parametrize("session_id,athlete_id", [("", "athlete"), ("  ", "athlete"), ("session", "")])
def test_session_identifiers_must_be_non_empty(session_id, athlete_id):
    with pytest.raises(DomainInvariantError):
        RecognitionSession(session_id=session_id, athlete_id=athlete_id)


@pytest.mark.parametrize("frame_index", [-1, True, 1.5])
def test_captured_frame_rejects_invalid_indices(frame_index):
    with pytest.raises(DomainInvariantError):
        CapturedFrame(frame_index=frame_index, timestamp_seconds=0, payload=object())


@pytest.mark.parametrize("timestamp", [-1, math.inf, math.nan, True, "1"])
def test_captured_frame_rejects_invalid_timestamps(timestamp):
    with pytest.raises(DomainInvariantError):
        CapturedFrame(frame_index=0, timestamp_seconds=timestamp, payload=object())


def test_captured_frame_requires_payload():
    with pytest.raises(DomainInvariantError, match="payload"):
        CapturedFrame(frame_index=0, timestamp_seconds=0, payload=None)


@pytest.mark.parametrize("angle", [-0.1, 180.1, math.inf, math.nan, True, "90"])
def test_angles_reject_values_outside_finite_degree_range(angle):
    with pytest.raises(DomainInvariantError):
        BiomechanicalAngles(left_knee_deg=angle)


def test_frame_result_validates_session_index_timestamp_and_angles():
    session = RecognitionSessionFactory()
    good = BiomechanicalAngles()
    for kwargs in (
        {
            "session": object(), "frame_index": 0, "timestamp_seconds": 0,
            "angles": good, "pose_detected": True,
        },
        {
            "session": session, "frame_index": -1, "timestamp_seconds": 0,
            "angles": good, "pose_detected": True,
        },
        {
            "session": session, "frame_index": True, "timestamp_seconds": 0,
            "angles": good, "pose_detected": True,
        },
        {
            "session": session, "frame_index": 0, "timestamp_seconds": math.inf,
            "angles": good, "pose_detected": True,
        },
        {
            "session": session, "frame_index": 0, "timestamp_seconds": -1,
            "angles": good, "pose_detected": True,
        },
        {
            "session": session, "frame_index": 0, "timestamp_seconds": 0,
            "angles": object(), "pose_detected": True,
        },
        {
            "session": session, "frame_index": 0, "timestamp_seconds": 0,
            "angles": good, "pose_detected": "yes",
        },
    ):
        with pytest.raises(DomainInvariantError):
            BiomechanicalFrameResult(**kwargs)


def test_landmark_validates_finite_coordinates_and_visibility():
    for values in ((math.nan, 0, 1), (0, math.inf, 1), (0, 0, -0.1), (0, 0, 1.1), (True, 0, 1)):
        with pytest.raises(DomainInvariantError):
            PoseLandmark2D(*values)


def test_calculate_angles_returns_ninety_degree_knee_on_non_square_image():
    landmarks = {
        LEFT_HIP: _landmark(0.25, 0.25),
        LEFT_KNEE: _landmark(0.25, 0.50),
        LEFT_ANKLE: _landmark(0.50, 0.50),
        LEFT_FOOT_INDEX: _landmark(0.75, 0.50),
        LEFT_SHOULDER: _landmark(0.25, 0.10),
        RIGHT_SHOULDER: _landmark(0.75, 0.10),
        RIGHT_HIP: _landmark(0.75, 0.25),
        RIGHT_KNEE: _landmark(0.75, 0.50),
        RIGHT_ANKLE: _landmark(0.50, 0.50),
    }

    angles = calculate_biomechanical_angles(landmarks, image_width=200, image_height=100)

    assert angles.left_knee_deg == pytest.approx(90.0)
    assert angles.right_knee_deg == pytest.approx(90.0)
    assert angles.trunk_angle_deg == pytest.approx(0.0)


def test_missing_and_low_visibility_landmarks_only_invalidate_dependent_angles():
    landmarks = {
        LEFT_HIP: _landmark(0.2, 0.2),
        LEFT_KNEE: _landmark(0.2, 0.5, visibility=0.49),
        LEFT_ANKLE: _landmark(0.4, 0.5),
        LEFT_SHOULDER: _landmark(0.2, 0.1),
        RIGHT_HIP: _landmark(0.8, 0.2),
        RIGHT_SHOULDER: _landmark(0.8, 0.1),
    }

    angles = calculate_biomechanical_angles(landmarks, 100, 100)

    assert angles.left_knee_deg is None
    assert angles.left_hip_deg is None
    assert angles.left_ankle_deg is None
    assert angles.right_knee_deg is None
    assert angles.trunk_angle_deg == pytest.approx(0.0)


def test_degenerate_segments_and_unavailable_trunk_return_none():
    same_point = _landmark(0.5, 0.5)
    angles = calculate_biomechanical_angles(
        {LEFT_HIP: same_point, LEFT_KNEE: same_point, LEFT_ANKLE: _landmark(0.8, 0.5)},
        100,
        100,
    )
    assert angles.left_knee_deg is None
    assert angles.trunk_angle_deg is None


@pytest.mark.parametrize(
    "landmarks,width,height,threshold",
    [
        ([], 100, 100, 0.5),
        ({}, 0, 100, 0.5),
        ({}, 100, True, 0.5),
        ({}, 100, 100, math.nan),
        ({LEFT_HIP: object()}, 100, 100, 0.5),
    ],
)
def test_calculator_rejects_invalid_inputs(landmarks, width, height, threshold):
    with pytest.raises(DomainInvariantError):
        calculate_biomechanical_angles(
            landmarks,
            image_width=width,
            image_height=height,
            visibility_threshold=threshold,
        )


def test_visibility_threshold_is_inclusive_and_zero_degree_angle_is_valid():
    landmarks = {
        LEFT_HIP: _landmark(0.1, 0.5),
        LEFT_KNEE: _landmark(0.5, 0.5, visibility=0.5),
        LEFT_ANKLE: _landmark(0.9, 0.5),
    }

    angles = calculate_biomechanical_angles(landmarks, 100, 100, visibility_threshold=0.5)

    assert angles.left_knee_deg == pytest.approx(180.0)
    assert angles.validity["left_knee_deg"] is True


def test_domain_landmark_keys_are_anatomical_enum_members_not_model_indices():
    assert LEFT_HIP is PoseLandmarkName.LEFT_HIP
    assert LEFT_KNEE is PoseLandmarkName.LEFT_KNEE
    angles = calculate_biomechanical_angles(
        {
            LEFT_HIP: _landmark(0.1, 0.5),
            LEFT_KNEE: _landmark(0.5, 0.5),
            LEFT_ANKLE: _landmark(0.9, 0.5),
        },
        image_width=100,
        image_height=100,
    )
    assert angles.left_knee_deg == pytest.approx(180.0)
    with pytest.raises(DomainInvariantError, match="PoseLandmarkName"):
        calculate_biomechanical_angles({23: _landmark(0.1, 0.5)}, 100, 100)


@pytest.mark.parametrize(
    "points,expected",
    [
        (((0, 1), (0, 0), (1, 0)), 90.0),
        (((-1, 0), (0, 0), (1, 0)), 180.0),
        (((1, 1), (0, 0), (2, 2)), 0.0),
        (((0, 0), (0, 0), (1, 0)), None),
    ],
)
def test_calculate_angle_at_handles_regular_and_degenerate_geometry(points, expected):
    angle = calculate_angle_at(*points)
    if expected is None:
        assert angle is None
    else:
        assert angle == pytest.approx(expected, abs=1e-5)


@pytest.mark.parametrize(
    "points",
    [
        ((0, 0), (0, 0, 1), (1, 0)),
        ((0, 0), (math.nan, 0), (1, 0)),
        ((True, 0), (0, 0), (1, 0)),
    ],
)
def test_calculate_angle_at_rejects_invalid_points(points):
    with pytest.raises(DomainInvariantError):
        calculate_angle_at(*points)

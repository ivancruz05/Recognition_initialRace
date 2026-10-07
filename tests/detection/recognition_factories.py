"""Small factory_boy fixtures for the new recognition-layer value objects."""

import factory

from detection.domain.entities import (
    BiomechanicalAngles,
    BiomechanicalFrameResult,
    CapturedFrame,
    RecognitionSession,
)
from detection.domain.landmarks import PoseLandmark2D


class PoseLandmark2DFactory(factory.Factory):
    class Meta:
        model = PoseLandmark2D

    x = 0.5
    y = 0.5
    visibility = 1.0


class RecognitionSessionFactory(factory.Factory):
    class Meta:
        model = RecognitionSession

    session_id = "session-001"
    athlete_id = "athlete-001"


class CapturedFrameFactory(factory.Factory):
    class Meta:
        model = CapturedFrame

    frame_index = 0
    timestamp_seconds = 0.0
    payload = factory.LazyFunction(object)


class BiomechanicalAnglesFactory(factory.Factory):
    class Meta:
        model = BiomechanicalAngles

    left_knee_deg = 90.0


class BiomechanicalFrameResultFactory(factory.Factory):
    class Meta:
        model = BiomechanicalFrameResult

    session = factory.SubFactory(RecognitionSessionFactory)
    frame_index = 0
    timestamp_seconds = 0.0
    angles = factory.SubFactory(BiomechanicalAnglesFactory)
    pose_detected = True

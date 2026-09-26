"""Pydantic request/response contracts for the HTTP API."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class KinematicsSummary(BaseModel):
    max_velocity_ms: Optional[float] = None
    average_velocity_ms: Optional[float] = None
    total_distance_m: Optional[float] = None


class AnalyzeResponse(BaseModel):
    video_path: str
    fps: float
    frames_processed: int
    calibration_valid: bool
    posture_score: float
    trunk_angle_deg: float
    variables: Dict[str, float] = Field(default_factory=dict)
    kinematics: Optional[KinematicsSummary] = None


class BodyMeasurementsResponse(BaseModel):
    height_cm: float
    leg_length_cm: float
    arm_length_cm: float
    torso_length_cm: float
    foot_length_cm: float
    shoulder_width_cm: float
    confidence: float


class AnalyzeReportResponse(BaseModel):
    athlete_name: str
    video_path: str
    frames_analyzed: int
    measurements: BodyMeasurementsResponse
    recommendations: List[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str

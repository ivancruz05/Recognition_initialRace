"""Shared feature schema for sprint machine-learning models."""

from __future__ import annotations

from typing import Dict, Iterable, List

import pandas as pd


DEFAULT_FEATURE_COLUMNS: List[str] = [
    "age",
    "height_cm",
    "weight_kg",
    "experience_years",
    "training_level",
    "sex_encoded",
    "avg_knee_angle",
    "avg_hip_angle",
    "trunk_angle",
    "knee_symmetry",
    "hip_symmetry",
    "posture_score",
    "camera_height_m",
    "camera_distance_m",
    "camera_angle_deg",
    "lighting_lux",
    "signal_quality",
    "visibility_ratio",
    "tracking_confidence",
    "pose_confidence",
]


def validate_feature_columns(data: pd.DataFrame, columns: Iterable[str] = DEFAULT_FEATURE_COLUMNS) -> None:
    """Raise a useful error when a feature column is missing."""
    missing = sorted(set(columns) - set(data.columns))
    if missing:
        raise ValueError(f"Missing feature columns: {', '.join(missing)}")


def as_feature_frame(data: pd.DataFrame | Dict, columns: Iterable[str] = DEFAULT_FEATURE_COLUMNS) -> pd.DataFrame:
    """Return a feature DataFrame with the canonical column order."""
    columns = list(columns)
    frame = pd.DataFrame([data]) if isinstance(data, dict) else data.copy()
    validate_feature_columns(frame, columns)
    return frame[columns]

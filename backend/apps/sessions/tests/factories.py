"""Pure builders for the sessions test suite.

No Django, no database: only stdlib + the domain layer, so the same
builders serve the domain, application and API suites (the API suite
persists them through the real adapters).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from apps.sessions.domain import (
    UNIT_CADENCE,
    UNIT_POSTURE,
    UNIT_SPEED,
    UNIT_STRIDE,
    BiomechanicalMetrics,
    MetricValue,
    PostureMetric,
    SprintSession,
    TimeSeriesPoint,
)

__all__ = ["make_contract", "make_session"]

DEFAULT_TIMESTAMP = "2026-10-03T22:44:45+00:00"


def make_contract(**overrides) -> dict:
    """Minimum valid contract payload (monograph Tabla 8).

    A ``None`` override for a metric expresses "not captured" in the
    source; the validator maps it to ``NOT_AVAILABLE`` (never 0).
    """
    payload = {
        "session_id": "SES-001",
        "athlete_id": "ATL-0001",
        "timestamp": DEFAULT_TIMESTAMP,
        "test_type": "prueba de 10 m con salida de tacos",
        "metrics": {
            "posture": {
                "value": 82.0,
                "unit": "score",
                "parameter": "posture_score",
                "details": {"trunk_angle": 4.2},
            },
            "speed": {
                "avg": 5.4,
                "max": 7.1,
                "unit": UNIT_SPEED,
                "series": [{"t": 0.0, "v": 5.4}, {"t": 0.5, "v": 7.1}],
            },
            "stride": {"avg": 1.8, "max": 2.0, "unit": UNIT_STRIDE},
            "cadence": {"avg": 3.9, "unit": UNIT_CADENCE},
        },
        "metadata": {
            "source_system": "Athletic_Export_FaseI",
            "schema_version": "1.0.0",
        },
    }
    payload.update(overrides)
    return payload


def make_session(
    session_id: str = "SES-001",
    athlete_id: str = "ATL-0001",
    timestamp: Optional[datetime] = None,
    test_type: str = "prueba de 10 m con salida de tacos",
    posture: Optional[float] = 82.0,
    speed: Optional[float] = 5.4,
    stride: Optional[float] = 1.8,
    cadence: Optional[float] = 3.9,
    speed_peak: Optional[float] = None,
    speed_series: tuple = (),
    metadata: Optional[dict] = None,
) -> SprintSession:
    """Domain entity; a ``None`` metric means NOT_AVAILABLE (RF-09)."""
    return SprintSession(
        session_id=session_id,
        athlete_id=athlete_id,
        timestamp=timestamp or datetime(2026, 10, 3, 22, 44, 45, tzinfo=timezone.utc),
        test_type=test_type,
        metrics=BiomechanicalMetrics(
            posture=(
                PostureMetric.unavailable()
                if posture is None
                else PostureMetric.available(
                    posture, UNIT_POSTURE, parameter="posture_score"
                )
            ),
            speed=(
                MetricValue.unavailable(UNIT_SPEED)
                if speed is None
                else MetricValue.available(
                    speed, UNIT_SPEED, peak=speed_peak, series=speed_series
                )
            ),
            stride=(
                MetricValue.unavailable(UNIT_STRIDE)
                if stride is None
                else MetricValue.available(stride, UNIT_STRIDE)
            ),
            cadence=(
                MetricValue.unavailable(UNIT_CADENCE)
                if cadence is None
                else MetricValue.available(cadence, UNIT_CADENCE)
            ),
        ),
        metadata=metadata
        or {
            "source_system": "Athletic_Export_FaseI",
            "schema_version": "1.0.0",
        },
    )


def make_speed_series(*pairs) -> tuple[TimeSeriesPoint, ...]:
    """Series points from ``(t, value)`` pairs (domain value objects)."""
    return tuple(TimeSeriesPoint(t=t, value=value) for t, value in pairs)

"""Input and output DTOs for the sessions application layer.

Frozen dataclasses crossing the boundary toward ``interfaces/``. Domain
entities are converted here and never leave this layer.

Pure Python (stdlib + domain only): no Django, DRF or ORM types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from ..domain import BiomechanicalMetrics, SprintSession

__all__ = [
    "RequesterContext",
    "SessionFilterInput",
    "SeriesPointDTO",
    "VariableDTO",
    "SessionListItemDTO",
    "SessionDetailDTO",
    "DashboardSummaryDTO",
    "ComparisonPointDTO",
    "ComparisonVariableDTO",
    "ComparisonMatrixDTO",
    "IngestionErrorDTO",
    "IngestionResultDTO",
]

# Orden estable de las cuatro variables del dominio en todas las salidas.
VARIABLE_ORDER = ("posture", "speed", "stride", "cadence")


@dataclass(frozen=True)
class RequesterContext:
    """Who is asking: role plus the athlete linked to a student account.

    Built by the interface layer from the JWT-authenticated user and
    passed to every use case that must apply RBAC (RF-02).
    """

    role: str
    athlete_id: Optional[str] = None

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def can_read_all(self) -> bool:
        return self.role in ("teacher", "admin")


@dataclass(frozen=True)
class SessionFilterInput:
    """Filter set for CU-01/CU-02, already carrying the requester."""

    requester: RequesterContext
    athlete_id: Optional[str] = None
    session_id: Optional[str] = None
    test_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


@dataclass(frozen=True)
class SeriesPointDTO:
    t: float
    value: float


@dataclass(frozen=True)
class VariableDTO:
    """One of the four domain variables, ready to render (RF-05..RF-09).

    ``available=False`` means the origin declared the value absent: the
    interface MUST render the empty state instead of a zero.
    """

    name: str
    available: bool
    unit: str
    value: Optional[float] = None
    peak: Optional[float] = None
    parameter: Optional[str] = None
    details: tuple = ()
    series: tuple[SeriesPointDTO, ...] = ()


@dataclass(frozen=True)
class SessionListItemDTO:
    session_id: str
    athlete_id: str
    timestamp: datetime
    test_type: str
    available_variables: tuple[str, ...]
    source_system: str
    schema_version: Optional[str] = None


@dataclass(frozen=True)
class SessionDetailDTO:
    session_id: str
    athlete_id: str
    timestamp: datetime
    test_type: str
    source_system: str
    schema_version: Optional[str]
    observation: Optional[str]
    variables: tuple[VariableDTO, ...]


@dataclass(frozen=True)
class DashboardSummaryDTO:
    """KPI panel (CU-01 / HU-01 / RF-03)."""

    total_sessions: int
    total_athletes: int
    completeness: dict  # variable -> porcentaje 0-100 de sesiones disponibles
    averages: dict  # variable -> media de los valores disponibles | None
    latest_session: Optional[SessionListItemDTO]
    scope: str  # "all" para docente, "athlete:<id>" para estudiante


@dataclass(frozen=True)
class ComparisonPointDTO:
    session_id: str
    available: bool
    value: Optional[float]


@dataclass(frozen=True)
class ComparisonVariableDTO:
    name: str
    unit: str
    points: tuple[ComparisonPointDTO, ...]
    delta: Optional[float]  # Δ entre la primera y la última sesión (si ambas existen)


@dataclass(frozen=True)
class ComparisonMatrixDTO:
    sessions: tuple[SessionListItemDTO, ...]
    variables: tuple[ComparisonVariableDTO, ...]


@dataclass(frozen=True)
class IngestionErrorDTO:
    session_id: Optional[str]
    field: str
    message: str


@dataclass(frozen=True)
class IngestionResultDTO:
    accepted: int
    rejected: int
    session_ids: tuple[str, ...] = ()
    errors: tuple[IngestionErrorDTO, ...] = ()


def _source(metadata: dict) -> tuple[str, Optional[str], Optional[str]]:
    source = metadata.get("source_system") or ""
    schema = metadata.get("schema_version")
    observation = metadata.get("observation") or metadata.get("notes")
    return (
        source,
        schema if isinstance(schema, str) else None,
        observation if isinstance(observation, str) else None,
    )


def _variable_dto(name: str, metric) -> VariableDTO:
    """Map a domain metric (``MetricValue``/``PostureMetric``) to a DTO."""
    available = metric.is_available
    if name == "posture":
        return VariableDTO(
            name=name,
            available=available,
            unit=metric.unit,
            value=metric.value,
            parameter=metric.parameter,
            details=tuple(sorted(metric.details.items())),
        )
    return VariableDTO(
        name=name,
        available=available,
        unit=metric.unit,
        value=metric.value,
        peak=metric.peak,
        series=tuple(SeriesPointDTO(t=p.t, value=p.value) for p in metric.series),
    )


def _list_item(session: SprintSession) -> SessionListItemDTO:
    source, schema, _ = _source(session.metadata)
    return SessionListItemDTO(
        session_id=session.session_id,
        athlete_id=session.athlete_id,
        timestamp=session.timestamp,
        test_type=session.test_type,
        available_variables=session.available_variables,
        source_system=source,
        schema_version=schema,
    )


def _variables(metrics: BiomechanicalMetrics) -> tuple[VariableDTO, ...]:
    mapping = {
        "posture": metrics.posture,
        "speed": metrics.speed,
        "stride": metrics.stride,
        "cadence": metrics.cadence,
    }
    return tuple(_variable_dto(name, mapping[name]) for name in VARIABLE_ORDER)

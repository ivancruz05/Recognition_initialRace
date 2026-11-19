"""Domain entities for the sprint-session module (CADI Fase II).

Pure Python (stdlib only): no Django, DRF or third-party imports.

Modelling rules taken from the monograph data contract (Cap. 7):

* ``AvailabilityStatus.NOT_AVAILABLE`` represents an absent value. A
  ``None`` coming from the contract is NEVER stored as ``0.0`` (prohibition
  of the implicit zero, RF-09).
* ``MetricValue.unit`` is mandatory: the system renders the unit it
  received and performs no silent conversion.
* The four domain variables (posture, speed, stride, cadence) are always
  present on a session, each one carrying its own availability status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence

from .exceptions import InvalidSessionData

__all__ = [
    "AvailabilityStatus",
    "TimeSeriesPoint",
    "MetricValue",
    "PostureMetric",
    "BiomechanicalMetrics",
    "SprintSession",
    "TrainingSession",
    "TRAINING_ATTENDANCE_STATUSES",
    "UNIT_POSTURE",
    "UNIT_SPEED",
    "UNIT_STRIDE",
    "UNIT_CADENCE",
]

# Unidades canónicas declaradas por el contrato de entrada. Se usan solo
# para rotular una métrica ausente; jamás para convertir valores.
UNIT_POSTURE = "deg"
UNIT_SPEED = "m/s"
UNIT_STRIDE = "m"
UNIT_CADENCE = "pasos/s"
TRAINING_ATTENDANCE_STATUSES = ("present", "absent", "excused")


class AvailabilityStatus(Enum):
    """Estado de disponibilidad de una métrica (RF-09)."""

    AVAILABLE = "AVAILABLE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


def _is_number(value: Any) -> bool:
    """True para int/float reales (excluye ``bool``, que hereda de int)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class TimeSeriesPoint:
    """Un par ``(t, valor)`` de una serie temporal declarada en el origen.

    ``t`` es el eje declarado por la fuente (segundos o número de paso);
    ``value`` es el valor medido. El dominio no inventa ejes ni interpola.
    """

    t: float
    value: float

    def __post_init__(self) -> None:
        if not _is_number(self.t):
            raise InvalidSessionData(
                f"series point t must be a number, got {type(self.t).__name__}",
                field="series",
            )
        if not _is_number(self.value):
            raise InvalidSessionData(
                f"series point value must be a number, got {type(self.value).__name__}",
                field="series",
            )


@dataclass(frozen=True)
class MetricValue:
    """Value object: valor escalar de una variable + unidad + estado.

    Invariants:
        * ``unit``: cadena no vacía (inmutabilidad de unidades);
        * ``NOT_AVAILABLE`` ⇒ ``value`` y ``peak`` son ``None`` (nunca 0.0);
        * ``AVAILABLE`` ⇒ ``value`` es un número real;
        * ``series``: tupla inmutable de :class:`TimeSeriesPoint`.
    """

    value: float | None
    unit: str
    status: AvailabilityStatus
    peak: float | None = None
    series: tuple[TimeSeriesPoint, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise InvalidSessionData("unit must be a non-empty str", field="unit")
        if not isinstance(self.status, AvailabilityStatus):
            raise InvalidSessionData(
                "status must be an AvailabilityStatus", field="status"
            )
        if not isinstance(self.series, tuple):
            raise InvalidSessionData("series must be a tuple", field="series")

        if self.status is AvailabilityStatus.NOT_AVAILABLE:
            # Anti-cero implícito: ausente = None, jamás 0.0.
            if self.value is not None or self.peak is not None:
                raise InvalidSessionData(
                    "NOT_AVAILABLE metrics must carry value=None and peak=None",
                    field="value",
                )
            return

        if not _is_number(self.value):
            raise InvalidSessionData(
                "AVAILABLE metrics need a numeric value", field="value"
            )
        if self.peak is not None and not _is_number(self.peak):
            raise InvalidSessionData("peak must be a number or None", field="peak")

    @classmethod
    def available(
        cls,
        value: float,
        unit: str,
        peak: float | None = None,
        series: Sequence[TimeSeriesPoint] = (),
    ) -> "MetricValue":
        return cls(
            value=value,
            unit=unit,
            status=AvailabilityStatus.AVAILABLE,
            peak=peak,
            series=tuple(series),
        )

    @classmethod
    def unavailable(cls, unit: str) -> "MetricValue":
        """Instancia ``NOT_AVAILABLE`` con valor ``None`` (nunca 0.0)."""
        return cls(value=None, unit=unit, status=AvailabilityStatus.NOT_AVAILABLE)

    @property
    def is_available(self) -> bool:
        return self.status is AvailabilityStatus.AVAILABLE


@dataclass(frozen=True)
class PostureMetric:
    """Postura: objeto estructurado del contrato (valor + parámetro + details).

    Se renderiza tal cual lo entregó la Fase I: sin recalcular ángulos ni
    emitir calificaciones (RF-05).
    """

    value: float | None
    unit: str
    parameter: str
    status: AvailabilityStatus
    details: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise InvalidSessionData("unit must be a non-empty str", field="unit")
        if not isinstance(self.parameter, str) or not self.parameter.strip():
            raise InvalidSessionData(
                "parameter must be a non-empty str", field="parameter"
            )
        if not isinstance(self.status, AvailabilityStatus):
            raise InvalidSessionData(
                "status must be an AvailabilityStatus", field="status"
            )
        if not isinstance(self.details, Mapping):
            raise InvalidSessionData("details must be a mapping", field="details")

        if self.status is AvailabilityStatus.NOT_AVAILABLE:
            if self.value is not None:
                raise InvalidSessionData(
                    "NOT_AVAILABLE posture must carry value=None", field="value"
                )
        elif not _is_number(self.value):
            raise InvalidSessionData(
                "AVAILABLE posture needs a numeric value", field="value"
            )

        for key, item in self.details.items():
            if not isinstance(key, str) or not _is_number(item):
                raise InvalidSessionData(
                    "posture details must map str -> number", field="details"
                )

    @classmethod
    def available(
        cls,
        value: float,
        unit: str,
        parameter: str,
        details: Mapping[str, float] | None = None,
    ) -> "PostureMetric":
        return cls(
            value=value,
            unit=unit,
            parameter=parameter,
            status=AvailabilityStatus.AVAILABLE,
            details=dict(details or {}),
        )

    @classmethod
    def unavailable(
        cls, parameter: str = "posture", unit: str = UNIT_POSTURE
    ) -> "PostureMetric":
        return cls(
            value=None,
            unit=unit,
            parameter=parameter,
            status=AvailabilityStatus.NOT_AVAILABLE,
            details={},
        )

    @property
    def is_available(self) -> bool:
        return self.status is AvailabilityStatus.AVAILABLE


@dataclass(frozen=True)
class BiomechanicalMetrics:
    """Agregado de las cuatro variables del dominio (Tabla 7).

    Siempre instanciado completo: una variable ausente llega como
    ``NOT_AVAILABLE``, nunca como cero.
    """

    posture: PostureMetric
    speed: MetricValue
    stride: MetricValue
    cadence: MetricValue

    def as_dict(self) -> dict:
        """Conveniencia para pruebas/serialización interna."""

        def metric(value: MetricValue) -> dict:
            return {
                "value": value.value,
                "unit": value.unit,
                "status": value.status.value,
                "peak": value.peak,
                "series_len": len(value.series),
            }

        return {
            "posture": {
                "value": self.posture.value,
                "unit": self.posture.unit,
                "parameter": self.posture.parameter,
                "status": self.posture.status.value,
            },
            "speed": metric(self.speed),
            "stride": metric(self.stride),
            "cadence": metric(self.cadence),
        }


@dataclass
class SprintSession:
    """A10 m sprint test registered by the Fase I export (contract, Tabla 8).

    Mutable on purpose: the repository assigns the surrogate ``id`` after
    persisting. ``session_id`` is the business key used end-to-end
    (trazabilidad, RF-10 / RNF-07).
    """

    session_id: str
    athlete_id: str
    timestamp: datetime
    test_type: str
    metrics: BiomechanicalMetrics
    metadata: dict = field(default_factory=dict)
    id: int | None = None
    training_session_id: int | None = None

    def __post_init__(self) -> None:
        self._validate_code("session_id", self.session_id)
        self._validate_code("athlete_id", self.athlete_id)
        self._validate_timestamp(self.timestamp)
        self._validate_code("test_type", self.test_type)
        if not isinstance(self.metrics, BiomechanicalMetrics):
            raise InvalidSessionData(
                "metrics must be a BiomechanicalMetrics instance", field="metrics"
            )
        if not isinstance(self.metadata, dict):
            raise InvalidSessionData("metadata must be a dict", field="metadata")
        if self.training_session_id is not None and (
            isinstance(self.training_session_id, bool)
            or not isinstance(self.training_session_id, int)
            or self.training_session_id <= 0
        ):
            raise InvalidSessionData(
                "training_session_id must be a positive int or None",
                field="training_session_id",
            )
        source = self.metadata.get("source_system")
        if not isinstance(source, str) or not source.strip():
            raise InvalidSessionData(
                "metadata.source_system is required (procedencia, RF-10)",
                field="metadata.source_system",
            )

    @staticmethod
    def _validate_code(field_name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise InvalidSessionData(
                f"{field_name} must be a non-empty str", field=field_name
            )
        if len(value) > 64:
            raise InvalidSessionData(
                f"{field_name} must be at most 64 chars", field=field_name
            )

    @staticmethod
    def _validate_timestamp(value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, datetime):
            raise InvalidSessionData(
                f"timestamp must be a datetime, got {type(value).__name__}",
                field="timestamp",
            )

    @property
    def available_variables(self) -> tuple[str, ...]:
        """Nombres (posture/speed/stride/cadence) con estado AVAILABLE."""
        pairs = (
            ("posture", self.metrics.posture),
            ("speed", self.metrics.speed),
            ("stride", self.metrics.stride),
            ("cadence", self.metrics.cadence),
        )
        return tuple(name for name, metric in pairs if metric.is_available)


@dataclass
class TrainingSession:
    """Individual training record for one athlete.

    Sprint measurements remain separate ``SprintSession`` records and are
    linked by their business IDs. The repository assigns ``id`` on save.
    """

    athlete_id: str
    timestamp: datetime
    duration_minutes: int
    training_type: str
    attendance_status: str
    coach: str = ""
    location: str = ""
    follow_up_notes: str = ""
    sprint_session_ids: tuple[str, ...] = ()
    id: int | None = None

    def __post_init__(self) -> None:
        SprintSession._validate_code("athlete_id", self.athlete_id)
        SprintSession._validate_timestamp(self.timestamp)
        if (
            isinstance(self.duration_minutes, bool)
            or not isinstance(self.duration_minutes, int)
            or self.duration_minutes < 1
            or self.duration_minutes > 1440
        ):
            raise InvalidSessionData(
                "duration_minutes must be an integer between 1 and 1440",
                field="duration_minutes",
            )
        self._validate_text("training_type", self.training_type, 120, required=True)
        if self.attendance_status not in TRAINING_ATTENDANCE_STATUSES:
            raise InvalidSessionData(
                "attendance_status must be present, absent or excused",
                field="attendance_status",
            )
        self._validate_text("coach", self.coach, 150)
        self._validate_text("location", self.location, 150)
        self._validate_text("follow_up_notes", self.follow_up_notes, 4000)
        if not isinstance(self.sprint_session_ids, tuple):
            raise InvalidSessionData(
                "sprint_session_ids must be a tuple", field="sprint_session_ids"
            )
        for session_id in self.sprint_session_ids:
            SprintSession._validate_code("sprint_session_ids", session_id)
        if len(set(self.sprint_session_ids)) != len(self.sprint_session_ids):
            raise InvalidSessionData(
                "sprint_session_ids must not contain duplicates",
                field="sprint_session_ids",
            )
        if self.id is not None and (
            isinstance(self.id, bool) or not isinstance(self.id, int) or self.id <= 0
        ):
            raise InvalidSessionData("id must be a positive int or None", field="id")

    @staticmethod
    def _validate_text(
        field_name: str, value: str, max_length: int, required: bool = False
    ) -> None:
        if not isinstance(value, str):
            raise InvalidSessionData(
                f"{field_name} must be a str", field=field_name
            )
        if required and not value.strip():
            raise InvalidSessionData(
                f"{field_name} must not be empty", field=field_name
            )
        if len(value) > max_length:
            raise InvalidSessionData(
                f"{field_name} must be at most {max_length} chars",
                field=field_name,
            )

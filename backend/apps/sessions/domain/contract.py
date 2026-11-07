"""Data contract (Tabla 8) + outbound port for contract validation.

``build_session`` is pure domain logic: it enforces the integrity rules
of Cap. 7.4 *before* anything reaches the domain entities or the
database. ``ContractValidatorPort`` is the swappable outbound port: the
JSON adapter lives in ``infrastructure/`` and simply adds transport
decoding on top of these rules.

Pure Python (stdlib only): no Django, DRF or format libraries.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

from .entities import (
    UNIT_CADENCE,
    UNIT_POSTURE,
    UNIT_SPEED,
    UNIT_STRIDE,
    AvailabilityStatus,
    BiomechanicalMetrics,
    MetricValue,
    PostureMetric,
    SprintSession,
    TimeSeriesPoint,
)
from .exceptions import InvalidContractError

__all__ = ["ContractValidatorPort", "ValidatedContract", "build_session"]

_REQUIRED_STRINGS = ("session_id", "athlete_id", "test_type")


@dataclass(frozen=True)
class ValidatedContract:
    """Outcome of a successful validation.

    Attributes:
        session: the domain entity ready to be persisted.
        athlete_label: optional academic label for the athlete record
            (``athlete_code_label`` of the contract).
        athlete_group: optional group/semester for the athlete record.
    """

    session: SprintSession
    athlete_label: Optional[str] = None
    athlete_group: Optional[str] = None


class ContractValidatorPort(ABC):
    """Outbound port: raw payload in, validated domain entity out."""

    @abstractmethod
    def validate(self, raw: Any) -> ValidatedContract:
        """Validate ``raw`` against the data contract.

        Raises:
            InvalidContractError: with a ``field -> message`` mapping when
                the payload does not satisfy the contract. The caller
                must not persist anything when this is raised.
        """


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_finite(value: float, field: str, errors: dict) -> None:
    if not math.isfinite(value):
        errors[field] = "must be a finite number"


def _optional_text(raw: Mapping, key: str, errors: dict, max_length: int = 120):
    """Optional non-empty string; records an error when present but blank."""
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors[key] = "must be a non-empty string when provided"
        return None
    if len(value) > max_length:
        errors[key] = "must be at most {0} chars".format(max_length)
        return None
    return value


def _parse_timestamp(value: Any, errors: dict) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        errors["timestamp"] = "is required (ISO 8601 string)"
        return None
    text = value.strip()
    if text.endswith(("Z", "z")):  # Python 3.9 fromisoformat no admite 'Z'
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        errors["timestamp"] = "must be a valid ISO 8601 datetime"
        return None


def _parse_series(
    raw: Any,
    field: str,
    errors: dict,
    keys: tuple,
) -> tuple[TimeSeriesPoint, ...]:
    """Parse an optional series ``[{"t":..,"v":..}, ...]``.

    ``keys`` maps the two accepted source keys per variable, e.g.
    ``("t", "v")`` for speed/cadence and ``("step", "length")`` for stride.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        errors[field] = "must be a list of points when provided"
        return ()

    axis_key, value_key = keys
    points = []
    for index, item in enumerate(raw):
        point_field = "{0}[{1}]".format(field, index)
        if not isinstance(item, Mapping):
            errors[point_field] = "must be an object with '{0}' and '{1}'".format(
                axis_key, value_key
            )
            continue
        axis, value = item.get(axis_key), item.get(value_key)
        if not _is_number(axis):
            errors[point_field] = "'{0}' must be a number".format(axis_key)
            continue
        if not _is_number(value):
            errors[point_field] = "'{0}' must be a number".format(value_key)
            continue
        if not math.isfinite(axis) or not math.isfinite(value):
            errors[point_field] = "must contain finite numbers"
            continue
        points.append(TimeSeriesPoint(t=axis, value=value))
    return tuple(points)


def _parse_metric(
    raw: Any,
    field: str,
    default_unit: str,
    errors: dict,
    series_keys: tuple,
    with_peak: bool,
) -> MetricValue:
    """Parse ``metrics.<name>`` (object | null) into a ``MetricValue``.

    Contract rules (RF-09 / Cap. 7.4):
      * ``null`` or absent → ``NOT_AVAILABLE`` with the canonical unit;
      * a numeric value REQUIRES its declared ``unit`` (no silent
        conversion, no implicit zero);
      * ``max`` becomes ``peak`` (only when declared).
    """
    if raw is None:
        return MetricValue.unavailable(default_unit)
    if not isinstance(raw, Mapping):
        errors[field] = "must be an object or null"
        return MetricValue.unavailable(default_unit)

    value = raw.get("avg")
    if value is None:
        value = raw.get("value")  # alias aceptado por compatibilidad
    unit = raw.get("unit")

    if value is None:
        # Ausencia declarada: nunca se convierte en 0.0.
        if unit is not None and (not isinstance(unit, str) or not unit.strip()):
            errors["{0}.unit".format(field)] = "must be a non-empty string"
        return MetricValue.unavailable(
            unit.strip() if isinstance(unit, str) and unit.strip() else default_unit
        )

    if not _is_number(value):
        errors["{0}.avg".format(field)] = "must be a number or null"
        return MetricValue.unavailable(default_unit)
    if not isinstance(unit, str) or not unit.strip():
        errors["{0}.unit".format(field)] = "is required when the metric has a value"
        return MetricValue.unavailable(default_unit)

    numeric_value = float(value)
    _check_finite(numeric_value, "{0}.avg".format(field), errors)

    peak = None
    if with_peak and raw.get("max") is not None:
        if not _is_number(raw.get("max")):
            errors["{0}.max".format(field)] = "must be a number or null"
        else:
            peak = float(raw.get("max"))
            _check_finite(peak, "{0}.max".format(field), errors)

    series = _parse_series(raw.get("series"), "{0}.series".format(field), errors, series_keys)

    if any(key.startswith(field) for key in errors):
        # Un error registrado invalida la métrica completa: se conserva la
        # ausencia en lugar de persistir un dato dudoso.
        return MetricValue.unavailable(default_unit)

    return MetricValue(
        value=numeric_value,
        unit=unit.strip(),
        status=AvailabilityStatus.AVAILABLE,
        peak=peak,
        series=series,
    )


def _parse_posture(raw: Any, errors: dict) -> PostureMetric:
    """Parse ``metrics.posture`` (object | null) into a ``PostureMetric``."""
    field = "metrics.posture"
    if raw is None:
        return PostureMetric.unavailable()
    if not isinstance(raw, Mapping):
        errors[field] = "must be an object or null"
        return PostureMetric.unavailable()

    value = raw.get("value")
    unit = raw.get("unit")
    parameter = raw.get("parameter")
    details = raw.get("details")

    if value is None:
        return PostureMetric.unavailable(
            parameter=parameter.strip()
            if isinstance(parameter, str) and parameter.strip()
            else "posture",
            unit=unit.strip() if isinstance(unit, str) and unit.strip() else UNIT_POSTURE,
        )

    if not _is_number(value):
        errors["{0}.value".format(field)] = "must be a number or null"
        return PostureMetric.unavailable()
    if not isinstance(unit, str) or not unit.strip():
        errors["{0}.unit".format(field)] = "is required when the metric has a value"
        return PostureMetric.unavailable()
    if not isinstance(parameter, str) or not parameter.strip():
        errors["{0}.parameter".format(field)] = "is required when the metric has a value"
        return PostureMetric.unavailable()

    numeric_value = float(value)
    _check_finite(numeric_value, "{0}.value".format(field), errors)

    clean_details: dict = {}
    if details is not None:
        if not isinstance(details, Mapping):
            errors["{0}.details".format(field)] = "must be an object"
        else:
            for key, item in details.items():
                detail_field = "{0}.details.{1}".format(field, key)
                if not isinstance(key, str) or not _is_number(item):
                    errors[detail_field] = "must map a name to a number"
                    continue
                if not math.isfinite(item):
                    errors[detail_field] = "must be a finite number"
                    continue
                clean_details[key] = float(item)

    if any(key.startswith(field) for key in errors):
        return PostureMetric.unavailable()

    return PostureMetric(
        value=numeric_value,
        unit=unit.strip(),
        parameter=parameter.strip(),
        status=AvailabilityStatus.AVAILABLE,
        details=clean_details,
    )


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def build_session(raw: Any) -> ValidatedContract:
    """Validate an incoming payload against the data contract (Tabla 8).

    Args:
        raw: decoded JSON object (``dict``).

    Returns:
        A :class:`ValidatedContract` with the domain entity and the
        optional athlete metadata.

    Raises:
        InvalidContractError: with every violation found; nothing must be
            persisted when this exception is raised (CP-01).
    """
    errors: dict = {}

    if not isinstance(raw, Mapping):
        raise InvalidContractError({"payload": "must be a JSON object"})

    # 1. Trazabilidad obligatoria -----------------------------------------
    for key in _REQUIRED_STRINGS:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            errors[key] = "is required (non-empty string)"
        elif len(value) > 64:
            errors[key] = "must be at most 64 chars"

    timestamp = _parse_timestamp(raw.get("timestamp"), errors)

    # 2. Procedencia obligatoria ------------------------------------------
    metadata = raw.get("metadata")
    if not isinstance(metadata, Mapping):
        errors["metadata"] = "is required (object with source_system)"
        metadata = {}
    else:
        source = metadata.get("source_system")
        if not isinstance(source, str) or not source.strip():
            errors["metadata.source_system"] = "is required (procedencia, RF-10)"
        schema_version = metadata.get("schema_version")
        if not isinstance(schema_version, str) or not schema_version.strip():
            errors["metadata.schema_version"] = (
                "is required (versioned export, RNF-09)"
            )

    # 3. Métricas opcionales (nulas -> NOT_AVAILABLE) ---------------------
    metrics_raw = raw.get("metrics", {})
    if metrics_raw is None:
        metrics_raw = {}
    if not isinstance(metrics_raw, Mapping):
        errors["metrics"] = "must be an object or null"
        metrics_raw = {}

    metrics = BiomechanicalMetrics(
        posture=_parse_posture(metrics_raw.get("posture"), errors),
        speed=_parse_metric(
            metrics_raw.get("speed"),
            "metrics.speed",
            UNIT_SPEED,
            errors,
            ("t", "v"),
            with_peak=True,
        ),
        stride=_parse_metric(
            metrics_raw.get("stride"),
            "metrics.stride",
            UNIT_STRIDE,
            errors,
            ("step", "length"),
            with_peak=True,
        ),
        cadence=_parse_metric(
            metrics_raw.get("cadence"),
            "metrics.cadence",
            UNIT_CADENCE,
            errors,
            ("t", "c"),
            with_peak=False,
        ),
    )

    # 4. Etiquetas opcionales del atleta ----------------------------------
    athlete_label = _optional_text(raw, "athlete_code_label", errors)
    athlete_group = _optional_text(raw, "athlete_group", errors)

    if errors:
        raise InvalidContractError(errors)

    session = SprintSession(
        session_id=raw["session_id"].strip(),
        athlete_id=raw["athlete_id"].strip(),
        timestamp=timestamp,
        test_type=raw["test_type"].strip(),
        metrics=metrics,
        metadata=dict(metadata),
    )
    return ValidatedContract(session=session, athlete_label=athlete_label, athlete_group=athlete_group)

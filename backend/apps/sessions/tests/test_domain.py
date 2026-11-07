"""Pruebas puras del dominio y contrato de sesiones (RF-09, RF-10)."""

from __future__ import annotations

import pytest

from apps.sessions.domain import (
    AvailabilityStatus,
    InvalidContractError,
    InvalidSessionData,
    MetricValue,
    PostureMetric,
    TimeSeriesPoint,
    build_session,
)

from .factories import make_contract


@pytest.mark.parametrize(
    "field,value",
    [
        ("session_id", ""),
        ("athlete_id", None),
        ("timestamp", "ayer"),
        ("test_type", " "),
        ("metadata", None),
    ],
)
def test_build_session_rechaza_campos_de_contrato_invalidos(field, value):
    payload = make_contract()
    payload[field] = value
    with pytest.raises(InvalidContractError) as error:
        build_session(payload)
    assert field in error.value.errors


def test_build_session_requiere_procedencia():
    payload = make_contract(metadata={"schema_version": "1.0.0"})
    with pytest.raises(InvalidContractError) as error:
        build_session(payload)
    assert "metadata.source_system" in error.value.errors


def test_build_session_requiere_version_de_esquema():
    payload = make_contract(metadata={"source_system": "CADI"})
    with pytest.raises(InvalidContractError) as error:
        build_session(payload)
    assert "metadata.schema_version" in error.value.errors


def test_build_session_mapea_metricas_nulas_a_no_disponibles_sin_cero():
    payload = make_contract(
        metrics={"posture": None, "speed": None, "stride": None, "cadence": None}
    )
    session = build_session(payload).session
    assert session.available_variables == ()
    for metric in (session.metrics.posture, session.metrics.speed, session.metrics.stride, session.metrics.cadence):
        assert metric.status is AvailabilityStatus.NOT_AVAILABLE
        assert metric.value is None


def test_cero_declarado_por_fuente_se_conserva_como_valor_disponible():
    payload = make_contract()
    payload["metrics"]["speed"]["avg"] = 0
    session = build_session(payload).session
    assert session.metrics.speed.is_available
    assert session.metrics.speed.value == 0.0


def test_build_session_conserva_serie_y_metadatos_de_trazabilidad():
    session = build_session(make_contract()).session
    assert session.metrics.speed.series[0].t == 0
    assert session.metadata["source_system"] == "Athletic_Export_FaseI"
    assert session.metadata["schema_version"] == "1.0.0"


def test_metric_value_no_permite_cero_implicito_en_no_disponible():
    with pytest.raises(InvalidSessionData, match="value=None"):
        MetricValue(value=0, unit="m/s", status=AvailabilityStatus.NOT_AVAILABLE)


def test_metric_value_disponible_requiere_unidad_y_valor_numerico():
    with pytest.raises(InvalidSessionData):
        MetricValue.available(None, "m/s")
    with pytest.raises(InvalidSessionData):
        MetricValue.unavailable(" ")


def test_posture_unavailable_conserva_none():
    posture = PostureMetric.unavailable()
    assert not posture.is_available
    assert posture.value is None


@pytest.mark.parametrize("t,value", [(True, 1), (0, False), ("0", 1)])
def test_time_series_point_rechaza_booleanos_y_texto(t, value):
    with pytest.raises(InvalidSessionData):
        TimeSeriesPoint(t=t, value=value)

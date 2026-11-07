"""Pruebas puras de las reglas R-00…R-05."""

from __future__ import annotations

from apps.analytics.domain import LIMITS_DISCLAIMER, MODEL_VERSION, RecommendationStatus
from apps.analytics.infrastructure import RuleBasedRecommendationAdapter
from apps.sessions.tests.factories import make_session


def test_r00_informa_datos_insuficientes_si_todo_esta_ausente():
    output = RuleBasedRecommendationAdapter().generate([
        make_session("SES-1", posture=None, speed=None, stride=None, cadence=None)
    ])
    assert len(output) == 1
    assert output[0].status is RecommendationStatus.INSUFFICIENT_DATA
    assert output[0].session_ids == ("SES-1",)


def test_r01_menciona_ausencia_sin_sustituir_por_cero():
    output = RuleBasedRecommendationAdapter().generate([
        make_session("SES-1", speed=None), make_session("SES-2", speed=5)
    ])
    missing = next(item for item in output if item.rule_id == "R-01" and "velocidad" in item.message)
    assert "no disponible" in missing.message.lower()
    assert "cero" in missing.message.lower()
    assert missing.session_ids == ("SES-1",)


def test_r02_speed_describes_first_last_delta_and_origin_sessions():
    output = RuleBasedRecommendationAdapter().generate([
        make_session("SES-1", speed=4.0), make_session("SES-2", speed=5.25)
    ])
    item = next(item for item in output if item.rule_id == "R-02")
    assert "4.0" in item.message and "5.25" in item.message and "+1.25" in item.message
    assert item.session_ids == ("SES-1", "SES-2")
    assert any("m/s" in evidence for evidence in item.evidence)


def test_r03_stride_y_r04_cadence_tienen_reglas_descriptivas():
    output = RuleBasedRecommendationAdapter().generate([
        make_session("SES-1", stride=1, cadence=2),
        make_session("SES-2", stride=1.5, cadence=3),
    ])
    assert {item.rule_id for item in output}.issuperset({"R-03", "R-04"})


def test_r05_reporta_postura_de_origen_con_parametro():
    output = RuleBasedRecommendationAdapter().generate([make_session("SES-1", posture=82)])
    item = next(item for item in output if item.rule_id == "R-05")
    assert "82" in item.message
    assert "posture_score" in item.message
    assert item.session_ids == ("SES-1",)


def test_todas_las_reglas_son_deterministas_y_muestran_limites():
    sessions = [make_session("SES-1", speed=4), make_session("SES-2", speed=5)]
    adapter = RuleBasedRecommendationAdapter()
    first, second = adapter.generate(sessions), adapter.generate(sessions)
    assert first == second
    assert all(item.limits == LIMITS_DISCLAIMER for item in first)
    assert MODEL_VERSION is None

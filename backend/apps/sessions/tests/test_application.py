"""Pruebas de casos de uso con repositorios in-memory (RNF-08, CP-07)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from apps.athletes.domain import Athlete, AthleteNotFound
from apps.sessions.application import (
    CompareSessions,
    GetDashboardSummary,
    GetSessionDetail,
    IngestSessionContract,
    ListSessionsByFilter,
    RequesterContext,
    SessionFilterInput,
)
from apps.sessions.domain import AccessDenied, InvalidContractError, SessionFilters, SessionNotFound
from apps.sessions.infrastructure.contract_validator import JsonContractValidator
from apps.sessions.infrastructure.mocks import InMemorySessionRepository

from .factories import make_contract, make_session


class FakeAthleteRepository:
    def __init__(self):
        self.items = {}

    def get_by_athlete_id(self, athlete_id):
        if athlete_id not in self.items:
            raise AthleteNotFound(athlete_id)
        return self.items[athlete_id]

    def add(self, athlete):
        self.items[athlete.athlete_id] = athlete
        return athlete


def test_list_sessions_aplica_filtro_y_orden_mas_reciente_primero():
    older = make_session("SES-OLD", timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
    newer = make_session("SES-NEW", timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc))
    other = make_session("SES-OTHER", athlete_id="ATL-0002")
    repo = InMemorySessionRepository([older, newer, other])
    use_case = ListSessionsByFilter(repo)
    filters = SessionFilterInput(requester=RequesterContext("teacher"), athlete_id="ATL-0001")
    assert [item.session_id for item in use_case.execute(filters)] == ["SES-NEW", "SES-OLD"]


def test_dashboard_ignora_metricas_ausentes_en_promedio():
    repo = InMemorySessionRepository([
        make_session("SES-1", speed=8.0),
        make_session("SES-2", speed=None),
    ])
    result = GetDashboardSummary(repo).execute(
        SessionFilterInput(requester=RequesterContext("teacher"))
    )
    assert result.total_sessions == 2
    assert result.averages["speed"] == 8.0
    assert result.completeness["speed"] == 50.0


def test_dashboard_sin_valores_disponibles_devuelve_none_no_cero():
    repo = InMemorySessionRepository([make_session("SES-1", posture=None, speed=None, stride=None, cadence=None)])
    result = GetDashboardSummary(repo).execute(
        SessionFilterInput(requester=RequesterContext("teacher"))
    )
    assert result.averages == {"posture": None, "speed": None, "stride": None, "cadence": None}


def test_student_solo_lista_su_atleta_e_ignora_filtro_de_otro():
    repo = InMemorySessionRepository([
        make_session("SES-OWN", athlete_id="ATL-0001"),
        make_session("SES-OTHER", athlete_id="ATL-0002"),
    ])
    filters = SessionFilterInput(
        requester=RequesterContext("student", "ATL-0001"), athlete_id="ATL-0002"
    )
    assert [item.session_id for item in ListSessionsByFilter(repo).execute(filters)] == ["SES-OWN"]


def test_student_sin_atleta_vinculado_no_ve_registros():
    repo = InMemorySessionRepository([make_session()])
    filters = SessionFilterInput(requester=RequesterContext("student"))
    assert ListSessionsByFilter(repo).execute(filters) == []


def test_detail_rechaza_estudiante_de_otro_atleta_y_desconocido():
    repo = InMemorySessionRepository([make_session()])
    use_case = GetSessionDetail(repo)
    with pytest.raises(AccessDenied):
        use_case.execute("SES-001", RequesterContext("student", "ATL-0002"))
    with pytest.raises(SessionNotFound):
        use_case.execute("missing", RequesterContext("teacher"))


def test_compare_calcula_delta_y_preserva_punto_ausente():
    repo = InMemorySessionRepository([
        make_session("SES-1", speed=5.0),
        make_session("SES-2", speed=None),
    ])
    result = CompareSessions(repo).execute(["SES-1", "SES-2"], RequesterContext("teacher"))
    speed = next(item for item in result.variables if item.name == "speed")
    assert speed.delta is None
    assert speed.points[1].available is False
    assert speed.points[1].value is None


def test_compare_requiere_dos_a_cuatro_sesiones():
    repo = InMemorySessionRepository([make_session()])
    with pytest.raises(Exception):
        CompareSessions(repo).execute(["SES-001"], RequesterContext("teacher"))


def test_ingest_acepta_lote_y_crea_atleta():
    repo = InMemorySessionRepository()
    athletes = FakeAthleteRepository()
    use_case = IngestSessionContract(repo, athletes, JsonContractValidator())
    result = use_case.execute([make_contract(), make_contract(session_id="SES-002")])
    assert result.accepted == 2
    assert result.rejected == 0
    assert set(result.session_ids) == {"SES-001", "SES-002"}
    assert "ATL-0001" in athletes.items


def test_ingest_invalido_es_atomico_y_no_persiste_sesiones():
    repo = InMemorySessionRepository()
    use_case = IngestSessionContract(repo, FakeAthleteRepository(), JsonContractValidator())
    valid = make_contract()
    invalid = make_contract(session_id="SES-BAD", timestamp="bad")
    result = use_case.execute([valid, invalid])
    assert result.accepted == 0
    assert result.rejected == 2
    assert not repo.exists("SES-001")
    assert result.errors[0].field == "timestamp"


def test_ingest_rechaza_duplicado_sin_mutar_repositorio():
    repo = InMemorySessionRepository()
    use_case = IngestSessionContract(repo, FakeAthleteRepository(), JsonContractValidator())
    assert use_case.execute(make_contract()).accepted == 1
    duplicate = use_case.execute(make_contract())
    assert duplicate.accepted == 0
    assert duplicate.rejected == 1
    assert len(repo.list(SessionFilters())) == 1

"""Pruebas HTTP de sesiones: JWT, RBAC, contrato y atomicidad."""

from __future__ import annotations

from copy import deepcopy

import pytest

from apps.sessions.infrastructure.models import SprintSessionModel

from .factories import make_contract


pytestmark = pytest.mark.django_db


def test_api_requires_authentication(api_client):
    assert api_client.get("/api/v1/sessions/").status_code == 401
    assert api_client.get("/api/v1/dashboard/summary/").status_code == 401


def test_teacher_can_list_detail_dashboard_and_compare(api_client, authenticate, seed_sessions, contract_payload):
    authenticate("teacher")
    second = make_contract(session_id="SES-002", athlete_id="ATL-0002")
    seed_sessions(contract_payload, second)
    assert api_client.get("/api/v1/sessions/").status_code == 200
    detail = api_client.get("/api/v1/sessions/SES-001/")
    assert detail.status_code == 200
    assert detail.json()["source"]["source_system"] == "Athletic_Export_FaseI"
    assert api_client.get("/api/v1/dashboard/summary/").json()["total_sessions"] == 2
    comparison = api_client.get("/api/v1/sessions/compare/?ids=SES-001,SES-002")
    assert comparison.status_code == 200
    assert len(comparison.json()["variables"]) == 4


def test_compare_bad_ids_and_unknown_session_return_400_and_404(api_client, authenticate):
    authenticate("teacher")
    assert api_client.get("/api/v1/sessions/compare/").status_code == 400
    assert api_client.get("/api/v1/sessions/missing/").status_code == 404


def test_student_reads_only_linked_athlete_and_cannot_ingest(api_client, authenticate, seed_sessions, contract_payload):
    from apps.athletes.infrastructure.models import Athlete

    seed_sessions(contract_payload, make_contract(session_id="SES-002", athlete_id="ATL-0002"))
    own = Athlete.objects.get(athlete_id="ATL-0001")
    authenticate("student", athlete=own)
    assert api_client.get("/api/v1/sessions/SES-001/").status_code == 200
    assert api_client.get("/api/v1/sessions/SES-002/").status_code == 403
    listed = api_client.get("/api/v1/sessions/").json()
    assert [item["session_id"] for item in listed] == ["SES-001"]
    assert api_client.post("/api/v1/sessions/ingest/", make_contract(session_id="SES-003"), format="json").status_code == 403


def test_ingest_valid_batch_returns_201_and_persists(api_client, authenticate):
    authenticate("teacher")
    response = api_client.post(
        "/api/v1/sessions/ingest/",
        [
            make_contract(session_id="SES-101"),
            make_contract(session_id="SES-102", athlete_id="ATL-0002"),
        ],
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["accepted"] == 2
    assert SprintSessionModel.objects.count() == 2


def test_ingest_invalid_batch_is_atomic(api_client, authenticate):
    authenticate("teacher")
    valid = make_contract(session_id="SES-201")
    invalid = make_contract(session_id="SES-202", timestamp="invalid")
    response = api_client.post("/api/v1/sessions/ingest/", [valid, invalid], format="json")
    assert response.status_code == 400
    assert response.json()["accepted"] == 0
    assert response.json()["rejected"] == 2
    assert response.json()["errors"]
    assert SprintSessionModel.objects.count() == 0


def test_detail_serializa_variable_ausente_com_null_y_no_cero(api_client, authenticate, seed_sessions):
    payload = make_contract(session_id="SES-301")
    payload["metrics"]["speed"] = None
    seed_sessions(payload)
    authenticate("teacher")
    response = api_client.get("/api/v1/sessions/SES-301/")
    assert response.status_code == 200
    speed = next(item for item in response.json()["variables"] if item["name"] == "speed")
    assert speed["available"] is False
    assert speed["value"] is None

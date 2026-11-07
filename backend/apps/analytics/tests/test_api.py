"""Pruebas HTTP del endpoint de analítica con JWT y RBAC."""

from __future__ import annotations

import pytest

from apps.athletes.infrastructure.models import Athlete
from apps.analytics.infrastructure.models import RecommendationRecord

from apps.sessions.tests.factories import make_contract


pytestmark = pytest.mark.django_db


def test_analytics_requires_authentication(api_client):
    assert api_client.get("/api/v1/analytics/recommendations/?ids=SES-1").status_code == 401


def test_teacher_response_includes_descriptive_traceability_and_limits(api_client, authenticate, seed_sessions, contract):
    authenticate("teacher")
    seed_sessions(contract, make_contract(session_id="SES-2", speed={"avg": 6.2, "unit": "m/s"}))
    response = api_client.get("/api/v1/analytics/recommendations/?ids=SES-001,SES-2")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["descriptive"]["sessions_analyzed"] == 2
    assert body["model_version"] is None
    assert body["evaluation"]["status"] == "PENDING_EVIDENCE"
    # Reading is side-effect free. Generation is an explicit POST action.
    assert body["recommendations"] == []
    assert RecommendationRecord.objects.count() == 0

    generated = api_client.post(
        "/api/v1/analytics/recommendations/generate/",
        {"session_ids": ["SES-001", "SES-2"]},
        format="json",
    )
    assert generated.status_code == 200, generated.json()
    outputs = generated.json()["recommendations"]
    assert outputs
    assert all(item["review_state"] in ("PENDING_REVIEW", "NOT_REQUIRED") for item in outputs)
    assert all(item["limits"] and item["evidence"] and item["session_ids"] for item in outputs)
    assert all(item["generated_at"] for item in outputs)
    assert any(item["review_state"] == "PENDING_REVIEW" for item in outputs)
    assert RecommendationRecord.objects.count() == len(outputs)

    # La misma entrada no crea registros duplicados.
    repeated = api_client.post(
        "/api/v1/analytics/recommendations/generate/",
        {"session_ids": ["SES-001", "SES-2"]},
        format="json",
    )
    assert repeated.status_code == 200
    assert {item["recommendation_id"] for item in repeated.json()["recommendations"]} == {
        item["recommendation_id"] for item in outputs
    }
    assert RecommendationRecord.objects.count() == len(outputs)


def test_analytics_requires_ids_and_returns_404_for_unknown(api_client, authenticate):
    authenticate("teacher")
    assert api_client.get("/api/v1/analytics/recommendations/").status_code == 400
    assert api_client.get("/api/v1/analytics/recommendations/?ids=missing").status_code == 404


def test_student_lists_only_approved_own_recommendations(api_client, authenticate, seed_sessions, contract):
    seed_sessions(contract, make_contract(session_id="SES-2", athlete_id="ATL-0002"))
    athlete = Athlete.objects.get(athlete_id="ATL-0001")
    authenticate("teacher")
    generated = api_client.post(
        "/api/v1/analytics/recommendations/generate/",
        {"session_ids": ["SES-001"]},
        format="json",
    )
    assert generated.status_code == 200
    recommendation = next(
        item
        for item in generated.json()["recommendations"]
        if item["status"] == "GENERATED"
    )

    # Pending outputs are not visible to a student.
    authenticate("student", athlete=athlete)
    own_pending = api_client.get("/api/v1/analytics/recommendations/?ids=SES-001")
    assert own_pending.status_code == 200
    assert own_pending.json()["recommendations"] == []
    assert api_client.get("/api/v1/analytics/recommendations/?ids=SES-2").status_code == 403
    student_review = api_client.post(
        "/api/v1/analytics/recommendations/{0}/review/".format(
            recommendation["recommendation_id"]
        ),
        {"decision": "APPROVED"},
        format="json",
    )
    assert student_review.status_code == 403

    # Teacher review exposes an approved recommendation to its owner.
    logged_in_teacher = api_client.post(
        "/api/v1/auth/login/",
        {"email": "teacher@analytics.test", "password": "secret-analytics-123"},
        format="json",
    )
    assert logged_in_teacher.status_code == 200
    api_client.credentials(
        HTTP_AUTHORIZATION="Bearer " + logged_in_teacher.json()["access"]
    )
    review = api_client.post(
        "/api/v1/analytics/recommendations/{0}/review/".format(
            recommendation["recommendation_id"]
        ),
        {"decision": "APPROVED", "note": "Revisada para retroalimentación."},
        format="json",
    )
    assert review.status_code == 200, review.json()
    assert review.json()["review_state"] == "APPROVED"
    assert review.json()["review"]["review_note"] == "Revisada para retroalimentación."
    stored = RecommendationRecord.objects.get(
        recommendation_id=recommendation["recommendation_id"]
    )
    assert stored.review_state == "APPROVED"
    assert stored.reviewed_by_id is not None
    assert stored.reviewed_at is not None

    logged_in_student = api_client.post(
        "/api/v1/auth/login/",
        {"email": "student@analytics.test", "password": "secret-analytics-123"},
        format="json",
    )
    assert logged_in_student.status_code == 200
    api_client.credentials(
        HTTP_AUTHORIZATION="Bearer " + logged_in_student.json()["access"]
    )
    visible = api_client.get("/api/v1/analytics/recommendations/?ids=SES-001")
    assert visible.status_code == 200
    assert [item["recommendation_id"] for item in visible.json()["recommendations"]] == [
        recommendation["recommendation_id"]
    ]
    assert visible.json()["recommendations"][0]["review_state"] == "APPROVED"
    assert "review" not in visible.json()["recommendations"][0]


def test_review_rejects_second_decision_and_keeps_rejected_hidden(api_client, authenticate, seed_sessions, contract):
    seed_sessions(contract)
    athlete = Athlete.objects.get(athlete_id="ATL-0001")
    authenticate("teacher")
    generated = api_client.post(
        "/api/v1/analytics/recommendations/generate/",
        {"session_ids": ["SES-001"]},
        format="json",
    )
    recommendation = next(
        item for item in generated.json()["recommendations"] if item["status"] == "GENERATED"
    )
    url = "/api/v1/analytics/recommendations/{0}/review/".format(
        recommendation["recommendation_id"]
    )
    rejected = api_client.post(url, {"decision": "REJECTED"}, format="json")
    assert rejected.status_code == 200
    assert rejected.json()["review_state"] == "REJECTED"
    again = api_client.post(url, {"decision": "APPROVED"}, format="json")
    assert again.status_code == 409

    authenticate("student", athlete=athlete)
    visible = api_client.get("/api/v1/analytics/recommendations/?ids=SES-001")
    assert visible.status_code == 200
    assert visible.json()["recommendations"] == []


def test_generation_and_review_are_docente_only_and_invalid_payload_is_400(api_client, authenticate, seed_sessions, contract):
    seed_sessions(contract)
    athlete = Athlete.objects.get(athlete_id="ATL-0001")
    authenticate("student", athlete=athlete)
    denied = api_client.post(
        "/api/v1/analytics/recommendations/generate/",
        {"session_ids": ["SES-001"]},
        format="json",
    )
    assert denied.status_code == 403

    authenticate("teacher")
    invalid = api_client.post(
        "/api/v1/analytics/recommendations/generate/", {"session_ids": []}, format="json"
    )
    assert invalid.status_code == 400
    missing = api_client.post(
        "/api/v1/analytics/recommendations/not-found/review/",
        {"decision": "APPROVED"},
        format="json",
    )
    assert missing.status_code == 404
    invalid_decision = api_client.post(
        "/api/v1/analytics/recommendations/not-found/review/",
        {"decision": "MAYBE"},
        format="json",
    )
    assert invalid_decision.status_code == 400


def test_technical_admin_does_not_receive_teacher_analytics(api_client, authenticate, seed_sessions, contract):
    seed_sessions(contract)
    authenticate("admin")
    assert api_client.get("/api/v1/analytics/recommendations/?ids=SES-001").status_code == 403

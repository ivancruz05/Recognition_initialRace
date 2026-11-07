"""Pruebas puras del caso de uso de analítica."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from apps.analytics.application import (
    GenerateRecommendations,
    GetAnalytics,
    ListRecommendations,
    ReviewRecommendation,
)
from apps.analytics.domain import (
    AnalyticsAccessDenied,
    NoSessionsToAnalyze,
    RecommendationAlreadyReviewed,
    RecommendationNotFound,
    ReviewState,
)
from apps.analytics.infrastructure import RuleBasedRecommendationAdapter
from apps.sessions.application import RequesterContext
from apps.sessions.domain import AccessDenied
from apps.sessions.infrastructure.mocks import InMemorySessionRepository
from apps.sessions.tests.factories import make_session


class InMemoryRecommendationRepository:
    """Fake del puerto de recomendaciones; no requiere SQL (RNF-08)."""

    def __init__(self):
        self.items = {}

    def save(self, recommendation, generated_by):
        fingerprint = (recommendation.rule_id, recommendation.session_ids, recommendation.evidence)
        for existing in self.items.values():
            if (existing.rule_id, existing.session_ids, existing.evidence) == fingerprint:
                return existing
        saved = replace(
            recommendation,
            recommendation_id="REC-PERSIST-{0}".format(len(self.items) + 1),
            generated_by=generated_by,
        )
        self.items[saved.recommendation_id] = saved
        return saved

    def list_for_sessions(self, session_ids, review_states=None):
        requested = set(session_ids)
        allowed = set(review_states) if review_states is not None else None
        return [
            item
            for item in self.items.values()
            if set(item.session_ids).issubset(requested)
            and (allowed is None or item.review_state in allowed)
        ]

    def review(self, recommendation_id, review_state, reviewer_id, reviewed_at, note=None):
        if recommendation_id not in self.items:
            raise RecommendationNotFound(recommendation_id)
        existing = self.items[recommendation_id]
        if existing.review_state is not ReviewState.PENDING_REVIEW:
            raise RecommendationAlreadyReviewed(recommendation_id)
        reviewed = replace(
            existing,
            review_state=review_state,
            reviewed_by=reviewer_id,
            reviewed_at=reviewed_at,
            review_note=note,
        )
        self.items[recommendation_id] = reviewed
        return reviewed


def test_analytics_rechaza_lista_vacia():
    use_case = GetAnalytics(InMemorySessionRepository(), RuleBasedRecommendationAdapter())
    with pytest.raises(NoSessionsToAnalyze):
        use_case.execute([], RequesterContext("teacher"))


def test_descriptiva_ignora_nulos_y_deduplica_atletas():
    repo = InMemorySessionRepository([
        make_session("SES-1", athlete_id="ATL-0001", speed=8, posture=None),
        make_session("SES-2", athlete_id="ATL-0001", speed=None, posture=None),
    ])
    result = GetAnalytics(repo, RuleBasedRecommendationAdapter()).execute(
        ["SES-1", "SES-2", "SES-1"], RequesterContext("teacher")
    )
    assert result.descriptive.sessions_analyzed == 2
    assert result.descriptive.athletes == ("ATL-0001",)
    assert result.descriptive.averages["speed"] == 8.0
    assert result.descriptive.completeness["speed"] == 50.0
    assert result.descriptive.averages["posture"] is None


def test_student_no_puede_analizar_sesion_de_otro_atleta():
    use_case = GetAnalytics(
        InMemorySessionRepository([make_session(athlete_id="ATL-0002")]),
        RuleBasedRecommendationAdapter(),
    )
    with pytest.raises(AccessDenied):
        use_case.execute(["SES-001"], RequesterContext("student", "ATL-0001"))


def test_student_propietario_y_docente_pueden_analizar():
    repo = InMemorySessionRepository([make_session()])
    use_case = GetAnalytics(repo, RuleBasedRecommendationAdapter())
    assert use_case.execute(["SES-001"], RequesterContext("student", "ATL-0001"))
    assert use_case.execute(["SES-001"], RequesterContext("teacher"))


def test_respuesta_indica_evaluacion_pendiente_y_modelo_no_disponible():
    repo = InMemorySessionRepository([make_session("SES-1", posture=None, speed=None, stride=None, cadence=None)])
    result = GetAnalytics(repo, RuleBasedRecommendationAdapter()).execute(
        ["SES-1"], RequesterContext("teacher")
    )
    assert result.execution_status == "INSUFFICIENT_DATA"
    assert result.model_version is None
    assert result.evaluation["status"] == "PENDING_EVIDENCE"


def test_generate_persists_pending_results_idempotently():
    sessions = InMemorySessionRepository([make_session("SES-1")])
    records = InMemoryRecommendationRepository()
    use_case = GenerateRecommendations(
        sessions, RuleBasedRecommendationAdapter(), records
    )
    first = use_case.execute(["SES-1"], RequesterContext("teacher"), generated_by=17)
    second = use_case.execute(["SES-1"], RequesterContext("teacher"), generated_by=17)
    assert first.recommendations
    assert all(item.review_state == "PENDING_REVIEW" for item in first.recommendations)
    assert all(item.generated_by == 17 for item in first.recommendations)
    assert len(records.items) == len(first.recommendations)
    assert {item.recommendation_id for item in first.recommendations} == {
        item.recommendation_id for item in second.recommendations
    }


def test_students_get_only_approved_recommendations_within_their_session_scope():
    sessions = InMemorySessionRepository([make_session("SES-1")])
    records = InMemoryRecommendationRepository()
    generate = GenerateRecommendations(sessions, RuleBasedRecommendationAdapter(), records)
    pending = generate.execute(["SES-1"], RequesterContext("teacher"), generated_by=17)
    review = ReviewRecommendation(records)
    approved_id = next(
        item.recommendation_id
        for item in pending.recommendations
        if item.status == "GENERATED"
    )
    review.execute(
        approved_id,
        ReviewState.APPROVED,
        requester=RequesterContext("teacher"),
        reviewer_id=17,
        note="Revisada",
    )

    list_use_case = ListRecommendations(
        sessions, RuleBasedRecommendationAdapter(), records
    )
    student = list_use_case.execute(["SES-1"], RequesterContext("student", "ATL-0001"))
    teacher = list_use_case.execute(["SES-1"], RequesterContext("teacher"))
    assert [item.recommendation_id for item in student.recommendations] == [approved_id]
    assert len(teacher.recommendations) == len(records.items)


def test_review_requires_pending_state_and_records_reviewer_and_timestamp():
    sessions = InMemorySessionRepository([make_session("SES-1")])
    records = InMemoryRecommendationRepository()
    generated = GenerateRecommendations(
        sessions, RuleBasedRecommendationAdapter(), records
    ).execute(["SES-1"], RequesterContext("teacher"), generated_by=17)
    target = next(item for item in generated.recommendations if item.status == "GENERATED")
    reviewed = ReviewRecommendation(records).execute(
        target.recommendation_id,
        ReviewState.REJECTED,
        requester=RequesterContext("teacher"),
        reviewer_id=21,
        note="Fuera de contexto",
    )
    assert reviewed.review_state == "REJECTED"
    assert reviewed.reviewed_by == 21
    assert reviewed.reviewed_at is not None
    assert reviewed.review_note == "Fuera de contexto"
    with pytest.raises(RecommendationAlreadyReviewed):
        ReviewRecommendation(records).execute(
            target.recommendation_id,
            ReviewState.APPROVED,
            requester=RequesterContext("teacher"),
            reviewer_id=21,
        )
    with pytest.raises(RecommendationNotFound):
        ReviewRecommendation(records).execute(
            "missing",
            ReviewState.APPROVED,
            requester=RequesterContext("teacher"),
            reviewer_id=21,
        )


def test_generation_and_review_use_cases_require_teacher_role():
    sessions = InMemorySessionRepository([make_session("SES-1")])
    records = InMemoryRecommendationRepository()
    generator = GenerateRecommendations(sessions, RuleBasedRecommendationAdapter(), records)
    with pytest.raises(AnalyticsAccessDenied):
        generator.execute(["SES-1"], RequesterContext("student", "ATL-0001"), generated_by=99)
    with pytest.raises(AnalyticsAccessDenied):
        ReviewRecommendation(records).execute(
            "REC-1",
            ReviewState.APPROVED,
            requester=RequesterContext("admin"),
            reviewer_id=99,
        )

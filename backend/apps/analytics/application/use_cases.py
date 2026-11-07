"""Application use cases for the analytics module.

RBAC (RF-02) is applied here, before any computation: a student can only
analyze sessions of their own linked athlete.

Pure Python (stdlib + domain only): no Django, DRF or ORM.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from statistics import mean
from typing import Optional, Sequence

from apps.sessions.application import RequesterContext
from apps.sessions.domain import (
    AccessDenied,
    SessionRepositoryPort,
    SprintSession,
)

from ..domain import (
    AnalyticsAccessDenied,
    NoSessionsToAnalyze,
    Recommendation,
    RecommendationPort,
    RecommendationRepositoryPort,
    RecommendationStatus,
    ReviewState,
)
from .dtos import AnalyticsResultDTO, DescriptiveSummaryDTO, RecommendationDTO

__all__ = ["GetAnalytics", "GenerateRecommendations", "ListRecommendations", "ReviewRecommendation"]

VARIABLE_ORDER = ("posture", "speed", "stride", "cadence")


def _metric_of(session: SprintSession, name: str):
    return {
        "posture": session.metrics.posture,
        "speed": session.metrics.speed,
        "stride": session.metrics.stride,
        "cadence": session.metrics.cadence,
    }[name]


def _check_access(session: SprintSession, requester: RequesterContext) -> None:
    """A student may only analyze sessions of their own linked athlete."""
    if requester.is_student and session.athlete_id != requester.athlete_id:
        raise AccessDenied(session.session_id, session.athlete_id)


class GetAnalytics:
    """Descriptive analytics + traceable recommendations (RF-11…RF-14).

    Orchestration only: the descriptive block is computed here (pure
    statistics over domain entities) and the recommendations come from
    the injected ``RecommendationPort`` adapter, so the method can be
    swapped without touching this class (§8.8).
    """

    def __init__(
        self,
        session_repository: SessionRepositoryPort,
        recommender: RecommendationPort,
    ) -> None:
        self._sessions = session_repository
        self._recommender = recommender

    def execute(
        self, session_ids: Sequence[str], requester: RequesterContext
    ) -> AnalyticsResultDTO:
        unique = list(dict.fromkeys(session_ids))
        if not unique:
            raise NoSessionsToAnalyze()

        sessions = []
        for session_id in unique:
            session = self._sessions.get_by_id(session_id)
            _check_access(session, requester)
            sessions.append(session)

        descriptive = self._describe(sessions)
        recommendations = tuple(
            RecommendationDTO.from_entity(item)
            for item in self._recommender.generate(sessions)
        )
        execution_status = (
            "INSUFFICIENT_DATA"
            if recommendations
            and all(
                item.status == RecommendationStatus.INSUFFICIENT_DATA.value
                for item in recommendations
            )
            else "EXECUTED"
        )
        return AnalyticsResultDTO(
            descriptive=descriptive,
            recommendations=recommendations,
            execution_status=execution_status,
        )

    # -- descriptive block (RF-11) ----------------------------------------
    @staticmethod
    def _describe(sessions: Sequence[SprintSession]) -> DescriptiveSummaryDTO:
        total = len(sessions)
        completeness: dict = {}
        averages: dict = {}
        min_max: dict = {}

        for name in VARIABLE_ORDER:
            values = [
                metric.value
                for session in sessions
                for metric in [_metric_of(session, name)]
                if metric.is_available and metric.value is not None
            ]
            completeness[name] = round(100.0 * len(values) / total, 1) if total else 0.0
            averages[name] = round(mean(values), 3) if values else None
            min_max[name] = (
                (round(min(values), 3), round(max(values), 3)) if values else None
            )

        return DescriptiveSummaryDTO(
            sessions_analyzed=total,
            athletes=tuple(
                sorted({session.athlete_id for session in sessions})
            ),
            completeness=completeness,
            averages=averages,
            min_max=min_max,
        )


class GenerateRecommendations:
    """Generate traceable outputs and persist them as pending teacher review."""

    def __init__(
        self,
        session_repository: SessionRepositoryPort,
        recommender: RecommendationPort,
        recommendation_repository: RecommendationRepositoryPort,
    ) -> None:
        self._analytics = GetAnalytics(session_repository, recommender)
        self._recommendations = recommendation_repository

    def execute(
        self,
        session_ids: Sequence[str],
        requester: RequesterContext,
        generated_by: int,
    ) -> AnalyticsResultDTO:
        if requester.role != "teacher":
            raise AnalyticsAccessDenied(requester.role, "generate recommendations")
        result = self._analytics.execute(session_ids, requester)
        saved = []
        for item in result.recommendations:
            entity = Recommendation(
                recommendation_id=item.recommendation_id,
                rule_id=item.rule_id,
                message=item.message,
                evidence=item.evidence,
                session_ids=item.session_ids,
                status=RecommendationStatus(item.status),
                review_state=ReviewState(item.review_state),
                limits=item.limits,
                dataset_version=item.dataset_version,
                model_version=item.model_version,
                generated_by=generated_by,
            )
            saved.append(
                RecommendationDTO.from_entity(
                    self._recommendations.save(entity, generated_by)
                )
            )
        return replace(result, recommendations=tuple(saved))


class ListRecommendations:
    """List stored outputs, exposing only approved items to students."""

    def __init__(
        self,
        session_repository: SessionRepositoryPort,
        recommender: RecommendationPort,
        recommendation_repository: RecommendationRepositoryPort,
    ) -> None:
        self._analytics = GetAnalytics(session_repository, recommender)
        self._recommendations = recommendation_repository

    def execute(
        self, session_ids: Sequence[str], requester: RequesterContext
    ) -> AnalyticsResultDTO:
        if requester.role not in ("teacher", "student"):
            raise AnalyticsAccessDenied(requester.role, "read analytics")
        # The use case checks existence and applies student ownership before
        # any saved recommendation is returned.
        result = self._analytics.execute(session_ids, requester)
        states = (ReviewState.APPROVED,) if requester.is_student else None
        saved = self._recommendations.list_for_sessions(session_ids, states)
        return replace(
            result,
            recommendations=tuple(
                RecommendationDTO.from_entity(item) for item in saved
            ),
        )


class ReviewRecommendation:
    """Record a one-time teacher decision on a pending recommendation."""

    def __init__(self, repository: RecommendationRepositoryPort) -> None:
        self._recommendations = repository

    def execute(
        self,
        recommendation_id: str,
        decision: ReviewState,
        requester: RequesterContext,
        reviewer_id: int,
        note: Optional[str] = None,
    ) -> RecommendationDTO:
        if requester.role != "teacher":
            raise AnalyticsAccessDenied(requester.role, "review recommendations")
        if decision not in (ReviewState.APPROVED, ReviewState.REJECTED):
            raise ValueError("decision must be APPROVED or REJECTED")
        recommendation = self._recommendations.review(
            recommendation_id=recommendation_id,
            review_state=decision,
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
            note=(note.strip() or None) if note is not None else None,
        )
        return RecommendationDTO.from_entity(recommendation)

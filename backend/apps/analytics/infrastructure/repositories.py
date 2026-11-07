"""Django adapter for the recommendation repository port."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import replace
from typing import Optional, Sequence

from django.db import IntegrityError, transaction

from ..domain import (
    Recommendation,
    RecommendationAlreadyReviewed,
    RecommendationNotFound,
    RecommendationRepositoryPort,
    RecommendationStatus,
    ReviewState,
)
from .models import RecommendationRecord

__all__ = ["DjangoRecommendationRepository"]


class DjangoRecommendationRepository(RecommendationRepositoryPort):
    """Persists outputs idempotently and records a one-time review decision."""

    def save(self, recommendation: Recommendation, generated_by: int) -> Recommendation:
        fingerprint = self._fingerprint(recommendation)
        defaults = {
            "recommendation_id": "REC-{0}".format(uuid.uuid4().hex),
            "rule_id": recommendation.rule_id,
            "message": recommendation.message,
            "evidence": list(recommendation.evidence),
            "session_ids": list(recommendation.session_ids),
            "status": recommendation.status.value,
            "review_state": recommendation.review_state.value,
            "limits": recommendation.limits,
            "dataset_version": recommendation.dataset_version,
            "model_version": recommendation.model_version,
            "generated_by_id": generated_by,
            "reviewed_by_id": recommendation.reviewed_by,
            "reviewed_at": recommendation.reviewed_at,
            "review_note": recommendation.review_note or "",
        }
        try:
            with transaction.atomic():
                record, _ = RecommendationRecord.objects.get_or_create(
                    fingerprint=fingerprint,
                    defaults=defaults,
                )
        except IntegrityError:
            # A concurrent generation with the same fingerprint won the
            # unique constraint; return that canonical record.
            record = RecommendationRecord.objects.get(fingerprint=fingerprint)
        return self._to_entity(record)

    def list_for_sessions(
        self,
        session_ids: Sequence[str],
        review_states: Optional[Sequence[ReviewState]] = None,
    ) -> list[Recommendation]:
        requested = set(session_ids)
        query = RecommendationRecord.objects.all()
        if review_states is not None:
            query = query.filter(review_state__in=[state.value for state in review_states])

        # JSON containment semantics differ across supported SQL engines.
        # Filter by the short, requested history in Python to keep the port
        # portable between SQLite tests and a production RDBMS.
        results = []
        for record in query:
            origins = set(record.session_ids or ())
            if origins and origins.issubset(requested):
                results.append(self._to_entity(record))
        return results

    def review(
        self,
        recommendation_id: str,
        review_state: ReviewState,
        reviewer_id: int,
        reviewed_at,
        note: Optional[str] = None,
    ) -> Recommendation:
        with transaction.atomic():
            try:
                record = RecommendationRecord.objects.select_for_update().get(
                    recommendation_id=recommendation_id
                )
            except RecommendationRecord.DoesNotExist:
                raise RecommendationNotFound(recommendation_id)

            if record.review_state != ReviewState.PENDING_REVIEW.value:
                raise RecommendationAlreadyReviewed(recommendation_id)

            record.review_state = review_state.value
            record.reviewed_by_id = reviewer_id
            record.reviewed_at = reviewed_at
            record.review_note = (note or "").strip()
            record.save(
                update_fields=(
                    "review_state",
                    "reviewed_by",
                    "reviewed_at",
                    "review_note",
                )
            )
        return self._to_entity(record)

    @staticmethod
    def _fingerprint(recommendation: Recommendation) -> str:
        identity = {
            "rule_id": recommendation.rule_id,
            "message": recommendation.message,
            "evidence": recommendation.evidence,
            "session_ids": recommendation.session_ids,
            "status": recommendation.status.value,
            "dataset_version": recommendation.dataset_version,
            "model_version": recommendation.model_version,
        }
        encoded = json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _to_entity(record: RecommendationRecord) -> Recommendation:
        return Recommendation(
            recommendation_id=record.recommendation_id,
            rule_id=record.rule_id,
            message=record.message,
            evidence=tuple(record.evidence or ()),
            session_ids=tuple(record.session_ids or ()),
            status=RecommendationStatus(record.status),
            review_state=ReviewState(record.review_state),
            limits=record.limits,
            dataset_version=record.dataset_version,
            model_version=record.model_version,
            generated_by=record.generated_by_id,
            generated_at=record.generated_at,
            reviewed_by=record.reviewed_by_id,
            reviewed_at=record.reviewed_at,
            review_note=record.review_note or None,
        )

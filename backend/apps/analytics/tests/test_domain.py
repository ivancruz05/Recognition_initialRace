"""Invariantes de la entidad de recomendación."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from apps.analytics.domain import (
    DATASET_VERSION,
    LIMITS_DISCLAIMER,
    MODEL_VERSION,
    Recommendation,
    RecommendationStatus,
    ReviewState,
)


def test_recommendation_default_is_traceable_and_pending_review():
    item = Recommendation("REC-1", "R-01", "Dato ausente", ("speed",), ("SES-1",))
    assert item.status is RecommendationStatus.GENERATED
    assert item.review_state is ReviewState.PENDING_REVIEW
    assert item.limits == LIMITS_DISCLAIMER
    with pytest.raises(FrozenInstanceError):
        item.message = "changed"


@pytest.mark.parametrize("message", ["", "   "])
def test_recommendation_requires_nonempty_message(message):
    with pytest.raises(ValueError):
        Recommendation("REC-1", "R-01", message, (), ())


def test_recommendation_requires_immutable_evidence_and_session_ids():
    with pytest.raises(ValueError):
        Recommendation("REC-1", "R-01", "message", ["evidence"], ())


def test_insufficient_data_factory_sets_explicit_status_and_rule():
    item = Recommendation.insufficient_data("REC-0", ["SES-1"], "sin métricas")
    assert item.rule_id == "R-00"
    assert item.status is RecommendationStatus.INSUFFICIENT_DATA
    assert item.session_ids == ("SES-1",)


def test_versions_do_not_claim_unvalidated_predictive_model():
    assert DATASET_VERSION
    assert MODEL_VERSION is None

"""DRF serializers for the analytics module.

Inbound: query-string parsing (``?ids=A,B``). Outbound: application DTOs
into JSON-ready dicts; domain entities never reach this layer.

Dependency rules (checked by @architecture-reviewer):
    * may import ``rest_framework`` and ``..application`` (DTOs only);
    * must NOT import ``..domain`` nor ``..infrastructure``.
"""

from __future__ import annotations

from rest_framework import serializers

from ..application import AnalyticsResultDTO, DescriptiveSummaryDTO

__all__ = [
    "parse_session_ids",
    "RecommendationGenerationSerializer",
    "RecommendationReviewInputSerializer",
    "AnalyticsResultSerializer",
]


def parse_session_ids(query_params) -> list[str]:
    """Map ``?ids=SES-01,SES-02`` into a list of session ids."""
    raw = query_params.get("ids", "")
    session_ids = [item.strip() for item in raw.split(",") if item.strip()]
    if not session_ids:
        raise serializers.ValidationError(
            {"ids": "The 'ids' query parameter is required (comma separated)."}
        )
    return session_ids


class RecommendationGenerationSerializer(serializers.Serializer):
    """IDs of source sessions for an explicit teacher-triggered generation."""

    session_ids = serializers.ListField(
        child=serializers.CharField(max_length=64, allow_blank=False),
        allow_empty=False,
        max_length=100,
    )


class RecommendationReviewInputSerializer(serializers.Serializer):
    """One-time decision made by a docente (HU-09)."""

    decision = serializers.ChoiceField(choices=("APPROVED", "REJECTED"))
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class AnalyticsResultSerializer:
    """``AnalyticsResultDTO`` → JSON (RF-11…RF-14, RF-09, RNF-11)."""

    @staticmethod
    def to_representation(
        dto: AnalyticsResultDTO, include_review_details: bool = False
    ) -> dict:
        return {
            "descriptive": AnalyticsResultSerializer._descriptive(dto.descriptive),
            "recommendations": [
                AnalyticsResultSerializer.recommendation(item, include_review_details)
                for item in dto.recommendations
            ],
            "execution_status": dto.execution_status,
            "dataset_version": dto.dataset_version,
            "model_version": dto.model_version,
            "evaluation": dto.evaluation,
            "limits": dto.limits,
        }

    @staticmethod
    def _descriptive(dto: DescriptiveSummaryDTO) -> dict:
        return {
            "sessions_analyzed": dto.sessions_analyzed,
            "athletes": list(dto.athletes),
            "completeness": dto.completeness,
            "averages": dto.averages,
            "min_max": dto.min_max,
        }

    @staticmethod
    def recommendation(dto, include_review_details: bool = False) -> dict:
        payload = {
            "recommendation_id": dto.recommendation_id,
            "rule_id": dto.rule_id,
            "message": dto.message,
            "evidence": list(dto.evidence),
            "session_ids": list(dto.session_ids),
            "status": dto.status,
            "review_state": dto.review_state,
            "limits": dto.limits,
            "dataset_version": dto.dataset_version,
            "model_version": dto.model_version,
            "generated_at": dto.generated_at.isoformat() if dto.generated_at else None,
            "reviewed_at": dto.reviewed_at.isoformat() if dto.reviewed_at else None,
        }
        if include_review_details:
            payload["review"] = {
                "generated_by": dto.generated_by,
                "reviewed_by": dto.reviewed_by,
                "review_note": dto.review_note,
            }
        return payload

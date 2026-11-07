"""DRF serializers for the sessions module.

Inbound: query-string / body parsing into application DTOs (shape only —
business truth stays in ``domain/``). Outbound: application DTOs into
JSON-ready dicts; the domain entities never reach this layer.

Dependency rules (checked by @architecture-reviewer):
    * may import ``rest_framework`` and ``..application`` (DTOs only);
    * must NOT import ``..domain`` nor ``..infrastructure``.
"""

from __future__ import annotations

from datetime import date, datetime

from rest_framework import serializers

from apps.accounts.application import GetMe
from apps.accounts.infrastructure import DjangoUserRepository

from ..application import (
    ComparisonMatrixDTO,
    DashboardSummaryDTO,
    IngestionResultDTO,
    RequesterContext,
    SessionDetailDTO,
    SessionFilterInput,
    SessionListItemDTO,
)

__all__ = [
    "parse_requester",
    "parse_filters",
    "SessionListItemSerializer",
    "SessionDetailSerializer",
    "DashboardSummarySerializer",
    "ComparisonSerializer",
    "IngestionResultSerializer",
]


def parse_requester(user) -> RequesterContext:
    """Build the RBAC context from the authenticated user.

    Goes through the accounts application layer (the accounts repository
    port), so this module never touches the ORM.
    """
    output = GetMe(DjangoUserRepository()).execute(user.id)
    return RequesterContext(role=output.user_type, athlete_id=output.athlete_id)


def _parse_date(value: str | None, field: str) -> date | None:
    if value in (None, ""):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise serializers.ValidationError(
            {field: "Use the YYYY-MM-DD format."}
        )


def parse_filters(query_params, requester: RequesterContext) -> SessionFilterInput:
    """Map ``?athlete_id=&session_id=&test_type=&date_from=&date_to=`` to DTO."""
    return SessionFilterInput(
        requester=requester,
        athlete_id=query_params.get("athlete_id") or None,
        session_id=query_params.get("session_id") or None,
        test_type=query_params.get("test_type") or None,
        date_from=_parse_date(query_params.get("date_from"), "date_from"),
        date_to=_parse_date(query_params.get("date_to"), "date_to"),
    )


def _iso(value: datetime) -> str:
    return value.isoformat()


class SessionListItemSerializer:
    """``SessionListItemDTO`` → JSON (trazabilidad, RF-10)."""

    @staticmethod
    def to_representation(dto: SessionListItemDTO) -> dict:
        return {
            "session_id": dto.session_id,
            "athlete_id": dto.athlete_id,
            "timestamp": _iso(dto.timestamp),
            "test_type": dto.test_type,
            "available_variables": list(dto.available_variables),
            "source_system": dto.source_system,
            "schema_version": dto.schema_version,
        }


class SessionDetailSerializer:
    """``SessionDetailDTO`` → JSON con las cuatro variables (RF-05…RF-09)."""

    @staticmethod
    def to_representation(dto: SessionDetailDTO) -> dict:
        return {
            "session_id": dto.session_id,
            "athlete_id": dto.athlete_id,
            "timestamp": _iso(dto.timestamp),
            "test_type": dto.test_type,
            "source": {
                "source_system": dto.source_system,
                "schema_version": dto.schema_version,
                "observation": dto.observation,
            },
            "variables": [
                SessionDetailSerializer._variable(variable) for variable in dto.variables
            ],
        }

    @staticmethod
    def _variable(variable) -> dict:
        payload = {
            "name": variable.name,
            "available": variable.available,
            "unit": variable.unit,
            "value": variable.value,
        }
        if variable.name == "posture":
            payload["parameter"] = variable.parameter
            payload["details"] = [
                {"name": name, "value": value} for name, value in variable.details
            ]
        else:
            payload["peak"] = variable.peak
            payload["series"] = [
                {"t": point.t, "value": point.value} for point in variable.series
            ]
        return payload


class DashboardSummarySerializer:
    """``DashboardSummaryDTO`` → JSON (tarjetas KPI, HU-01)."""

    @staticmethod
    def to_representation(dto: DashboardSummaryDTO) -> dict:
        latest = dto.latest_session
        return {
            "total_sessions": dto.total_sessions,
            "total_athletes": dto.total_athletes,
            "completeness": dto.completeness,
            "averages": dto.averages,
            "latest_session": (
                SessionListItemSerializer.to_representation(latest)
                if latest is not None
                else None
            ),
            "scope": dto.scope,
        }


class ComparisonSerializer:
    """``ComparisonMatrixDTO`` → JSON (HU-05, Δ y unidades visibles)."""

    @staticmethod
    def to_representation(dto: ComparisonMatrixDTO) -> dict:
        return {
            "sessions": [
                SessionListItemSerializer.to_representation(session)
                for session in dto.sessions
            ],
            "variables": [
                {
                    "name": variable.name,
                    "unit": variable.unit,
                    "delta": variable.delta,
                    "points": [
                        {
                            "session_id": point.session_id,
                            "available": point.available,
                            "value": point.value,
                        }
                        for point in variable.points
                    ],
                }
                for variable in dto.variables
            ],
        }


class IngestionResultSerializer:
    """``IngestionResultDTO`` → JSON (log de validación, vista /ingest)."""

    @staticmethod
    def to_representation(dto: IngestionResultDTO) -> dict:
        return {
            "accepted": dto.accepted,
            "rejected": dto.rejected,
            "session_ids": list(dto.session_ids),
            "errors": [
                {
                    "session_id": error.session_id,
                    "field": error.field,
                    "message": error.message,
                }
                for error in dto.errors
            ],
        }

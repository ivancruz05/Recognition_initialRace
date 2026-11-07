"""Application use cases for the sessions module (CU-01 … CU-05).

Each use case receives its outbound ports via constructor injection
(``SessionRepositoryPort``, ``ContractValidatorPort`` and, for the
ingestion case, the athletes port). Implementations live in
``infrastructure/`` and are wired at the interface boundary: this module
never imports them.

Pure Python (stdlib + domain only): no Django, DRF or ORM.

RBAC (RF-02) is applied HERE, not in the HTTP layer: a student request
is always scoped to their own linked athlete, even when the filter
carries another ``athlete_id`` (monograph §11.2).
"""

from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Mapping, Optional, Sequence

from apps.athletes.domain import Athlete, AthleteNotFound, AthleteRepository

from ..domain import (
    AccessDenied,
    ContractValidatorPort,
    InvalidContractError,
    InvalidSessionData,
    SessionFilters,
    SessionNotFound,
    SessionRepositoryPort,
    SprintSession,
)
from .dtos import (
    VARIABLE_ORDER,
    ComparisonMatrixDTO,
    ComparisonPointDTO,
    ComparisonVariableDTO,
    DashboardSummaryDTO,
    IngestionErrorDTO,
    IngestionResultDTO,
    RequesterContext,
    SessionDetailDTO,
    SessionFilterInput,
    SessionListItemDTO,
    VariableDTO,
    _list_item,
    _variables,
)

__all__ = [
    "ListSessionsByFilter",
    "GetDashboardSummary",
    "GetSessionDetail",
    "CompareSessions",
    "IngestSessionContract",
]


def _scoped_filters(filters: SessionFilterInput) -> Optional[SessionFilters]:
    """Translate the incoming filters into repository filters, applying RBAC.

    Returns:
        ``None`` when the requester must see nothing (a student without a
        linked athlete has no authorized records).
    """
    requester = filters.requester
    if requester.is_student:
        if not requester.athlete_id:
            return None
        # Se impone el vínculo: el parámetro entrante se ignora por completo.
        athlete_id = requester.athlete_id
    else:
        athlete_id = filters.athlete_id

    return SessionFilters(
        athlete_id=athlete_id,
        session_id=filters.session_id,
        test_type=filters.test_type,
        date_from=filters.date_from,
        date_to=filters.date_to,
    )


def _scope_label(filters: SessionFilterInput) -> str:
    requester = filters.requester
    if requester.is_student:
        return "athlete:{0}".format(requester.athlete_id or "-")
    if filters.athlete_id:
        return "athlete:{0}".format(filters.athlete_id)
    return "all"


def _check_access(session: SprintSession, requester: RequesterContext) -> None:
    """A student may only read sessions of their own linked athlete (RF-02)."""
    if requester.is_student and session.athlete_id != requester.athlete_id:
        raise AccessDenied(session.session_id, session.athlete_id)


def _metric_of(session: SprintSession, name: str):
    return {
        "posture": session.metrics.posture,
        "speed": session.metrics.speed,
        "stride": session.metrics.stride,
        "cadence": session.metrics.cadence,
    }[name]


# ---------------------------------------------------------------------------
# CU-02 — Listar y filtrar sesiones
# ---------------------------------------------------------------------------
class ListSessionsByFilter:
    """List sessions matching the filters, newest first (RF-04)."""

    def __init__(self, repository: SessionRepositoryPort) -> None:
        self._repository = repository

    def execute(self, filters: SessionFilterInput) -> list[SessionListItemDTO]:
        scoped = _scoped_filters(filters)
        if scoped is None:
            return []
        return [_list_item(session) for session in self._repository.list(scoped)]


# ---------------------------------------------------------------------------
# CU-01 — Resumen del dashboard
# ---------------------------------------------------------------------------
class GetDashboardSummary:
    """Aggregate KPIs for the panel (RF-03, HU-01).

    Averages ignore absent values: a ``NOT_AVAILABLE`` metric never
    contributes a zero to the historic mean (RF-09).
    """

    def __init__(self, repository: SessionRepositoryPort) -> None:
        self._repository = repository

    def execute(self, filters: SessionFilterInput) -> DashboardSummaryDTO:
        scoped = _scoped_filters(filters)
        empty_averages = {name: None for name in VARIABLE_ORDER}
        empty_completeness = {name: 0.0 for name in VARIABLE_ORDER}
        if scoped is None:
            return DashboardSummaryDTO(
                total_sessions=0,
                total_athletes=0,
                completeness=empty_completeness,
                averages=empty_averages,
                latest_session=None,
                scope=_scope_label(filters),
            )

        sessions = self._repository.list(scoped)
        total = len(sessions)

        if total == 0:
            return DashboardSummaryDTO(
                total_sessions=0,
                total_athletes=0,
                completeness=empty_completeness,
                averages=empty_averages,
                latest_session=None,
                scope=_scope_label(filters),
            )

        completeness: dict = {}
        averages: dict = {}
        for name in VARIABLE_ORDER:
            available_values = [
                metric.value
                for session in sessions
                for metric in [_metric_of(session, name)]
                if metric.is_available and metric.value is not None
            ]
            completeness[name] = round(100.0 * len(available_values) / total, 1)
            averages[name] = (
                round(mean(available_values), 3) if available_values else None
            )

        latest = max(sessions, key=lambda session: session.timestamp)
        return DashboardSummaryDTO(
            total_sessions=total,
            total_athletes=self._repository.count_athletes(scoped),
            completeness=completeness,
            averages=averages,
            latest_session=_list_item(latest),
            scope=_scope_label(filters),
        )


# ---------------------------------------------------------------------------
# CU-03 — Detalle de sesión
# ---------------------------------------------------------------------------
class GetSessionDetail:
    """Full detail of one session: the four variables with their units,
    series and availability states (RF-05 … RF-10).
    """

    def __init__(self, repository: SessionRepositoryPort) -> None:
        self._repository = repository

    def execute(self, session_id: str, requester: RequesterContext) -> SessionDetailDTO:
        session = self._repository.get_by_id(session_id)
        _check_access(session, requester)
        metadata = session.metadata
        schema = metadata.get("schema_version")
        observation = metadata.get("observation") or metadata.get("notes")
        return SessionDetailDTO(
            session_id=session.session_id,
            athlete_id=session.athlete_id,
            timestamp=session.timestamp,
            test_type=session.test_type,
            source_system=metadata.get("source_system", ""),
            schema_version=schema if isinstance(schema, str) else None,
            observation=observation if isinstance(observation, str) else None,
            variables=_variables(session.metrics),
        )


# ---------------------------------------------------------------------------
# CU-04 — Comparar sesiones
# ---------------------------------------------------------------------------
class CompareSessions:
    """Align 2…4 sessions under their own units and compute Δ (HU-05).

    Δ is a presentation delta between the first and the last selected
    session, computed only when BOTH values exist; otherwise the delta is
    ``None`` and the interface renders the empty state.
    """

    MIN_SESSIONS = 2
    MAX_SESSIONS = 4

    def __init__(self, repository: SessionRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self, session_ids: Sequence[str], requester: RequesterContext
    ) -> ComparisonMatrixDTO:
        unique = list(dict.fromkeys(session_ids))
        if not (self.MIN_SESSIONS <= len(unique) <= self.MAX_SESSIONS):
            raise InvalidSessionData(
                "session_ids must contain between {0} and {1} sessions".format(
                    self.MIN_SESSIONS, self.MAX_SESSIONS
                ),
                field="session_ids",
            )

        sessions = []
        for session_id in unique:
            session = self._repository.get_by_id(session_id)
            _check_access(session, requester)
            sessions.append(session)

        variables = []
        for name in VARIABLE_ORDER:
            metrics = [_metric_of(session, name) for session in sessions]
            unit = metrics[0].unit
            points = tuple(
                ComparisonPointDTO(
                    session_id=session.session_id,
                    available=metric.is_available,
                    value=metric.value,
                )
                for session, metric in zip(sessions, metrics)
            )
            first, last = metrics[0], metrics[-1]
            delta = None
            if (
                first.is_available
                and last.is_available
                and first.value is not None
                and last.value is not None
                and len(metrics) > 1
            ):
                delta = round(last.value - first.value, 3)
            variables.append(
                ComparisonVariableDTO(
                    name=name, unit=unit, points=points, delta=delta
                )
            )

        return ComparisonMatrixDTO(
            sessions=tuple(_list_item(session) for session in sessions),
            variables=tuple(variables),
        )


# ---------------------------------------------------------------------------
# CU-05 — Ingerir contrato de datos
# ---------------------------------------------------------------------------
class IngestSessionContract:
    """Validate and persist one contract payload or a batch of them.

    Atomic by design (CP-01): every record is validated *and* checked for
    duplicates before anything is written, so a rejected batch leaves the
    database untouched (RNF-03).
    """

    def __init__(
        self,
        session_repository: SessionRepositoryPort,
        athlete_repository: AthleteRepository,
        validator: ContractValidatorPort,
    ) -> None:
        self._sessions = session_repository
        self._athletes = athlete_repository
        self._validator = validator

    def execute(self, payload) -> IngestionResultDTO:
        records = payload if isinstance(payload, list) else [payload]
        if not records:
            return IngestionResultDTO(
                accepted=0,
                rejected=1,
                errors=(
                    IngestionErrorDTO(
                        session_id=None,
                        field="payload",
                        message="must be an object or a non-empty list of objects",
                    ),
                ),
            )

        validated = []
        errors: list[IngestionErrorDTO] = []
        for record in records:
            session_id = (
                record.get("session_id")
                if isinstance(record, Mapping) and isinstance(record.get("session_id"), str)
                else None
            )
            try:
                contract = self._validator.validate(record)
            except InvalidContractError as exc:
                for field_name, message in sorted(exc.errors.items()):
                    errors.append(
                        IngestionErrorDTO(
                            session_id=session_id, field=field_name, message=message
                        )
                    )
                continue

            if self._sessions.exists(contract.session.session_id):
                errors.append(
                    IngestionErrorDTO(
                        session_id=contract.session.session_id,
                        field="session_id",
                        message="already ingested (duplicate)",
                    )
                )
                continue
            validated.append(contract)

        if errors:
            # Nada se persiste: el lote completo queda rechazado.
            return IngestionResultDTO(
                accepted=0, rejected=len(records), errors=tuple(errors)
            )

        session_ids = []
        for contract in validated:
            athlete_error = self._ensure_athlete(contract)
            if athlete_error is not None:
                return IngestionResultDTO(
                    accepted=0,
                    rejected=len(records),
                    errors=(athlete_error,),
                )
            saved = self._sessions.add(contract.session)
            session_ids.append(saved.session_id)

        return IngestionResultDTO(
            accepted=len(session_ids), rejected=0, session_ids=tuple(session_ids)
        )

    def _ensure_athlete(self, contract) -> Optional[IngestionErrorDTO]:
        """Create the pseudonymous athlete record when it does not exist."""
        athlete_id = contract.session.athlete_id
        try:
            self._athletes.get_by_athlete_id(athlete_id)
        except AthleteNotFound:
            try:
                self._athletes.add(
                    Athlete(
                        athlete_id=athlete_id,
                        label=contract.athlete_label,
                        group=contract.athlete_group,
                        registered_at=contract.session.timestamp.date(),
                    )
                )
            except Exception as exc:  # domain error translated to the API
                return IngestionErrorDTO(
                    session_id=contract.session.session_id,
                    field="athlete_id",
                    message=str(exc),
                )
        return None

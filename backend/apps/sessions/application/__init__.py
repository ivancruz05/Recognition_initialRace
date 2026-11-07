"""Application layer of the sessions module.

Use cases plus their input/output DTOs. This package may import only
``backend.apps.sessions.domain``, ``backend.apps.athletes.domain`` (ports
of a sibling module) and the standard library: no Django, DRF,
``infrastructure/`` or ``interfaces/`` dependencies are allowed.
"""

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
    SeriesPointDTO,
    VariableDTO,
)
from .use_cases import (
    CompareSessions,
    GetDashboardSummary,
    GetSessionDetail,
    IngestSessionContract,
    ListSessionsByFilter,
)

__all__ = [
    "VARIABLE_ORDER",
    "ComparisonMatrixDTO",
    "ComparisonPointDTO",
    "ComparisonVariableDTO",
    "DashboardSummaryDTO",
    "IngestionErrorDTO",
    "IngestionResultDTO",
    "RequesterContext",
    "SessionDetailDTO",
    "SessionFilterInput",
    "SessionListItemDTO",
    "SeriesPointDTO",
    "VariableDTO",
    "CompareSessions",
    "GetDashboardSummary",
    "GetSessionDetail",
    "IngestSessionContract",
    "ListSessionsByFilter",
]

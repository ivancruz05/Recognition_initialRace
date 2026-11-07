"""Domain layer of the sessions module.

Only stdlib imports are allowed in this package (no Django, DRF,
application/, infrastructure/ or interfaces/). The re-exports below are
safe: they only reference modules of this same layer.
"""

from .contract import ContractValidatorPort, ValidatedContract, build_session
from .entities import (
    UNIT_CADENCE,
    UNIT_POSTURE,
    UNIT_SPEED,
    UNIT_STRIDE,
    AvailabilityStatus,
    BiomechanicalMetrics,
    MetricValue,
    PostureMetric,
    SprintSession,
    TimeSeriesPoint,
)
from .exceptions import (
    AccessDenied,
    DomainError,
    InvalidContractError,
    InvalidSessionData,
    SessionNotFound,
)
from .repositories import SessionFilters, SessionRepositoryPort

__all__ = [
    "AccessDenied",
    "AvailabilityStatus",
    "BiomechanicalMetrics",
    "ContractValidatorPort",
    "DomainError",
    "InvalidContractError",
    "InvalidSessionData",
    "MetricValue",
    "PostureMetric",
    "SessionFilters",
    "SessionNotFound",
    "SessionRepositoryPort",
    "SprintSession",
    "TimeSeriesPoint",
    "UNIT_CADENCE",
    "UNIT_POSTURE",
    "UNIT_SPEED",
    "UNIT_STRIDE",
    "ValidatedContract",
    "build_session",
]

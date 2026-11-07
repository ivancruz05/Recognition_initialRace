"""Outbound ports of the analytics module.

Pure Python (stdlib only): the port is an interface, the adapter lives in
``infrastructure/`` (rule-based today, a trained model tomorrow) and is
injected by the application layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence

from apps.sessions.domain import SprintSession

from .entities import Recommendation, ReviewState
from .exceptions import RecommendationAlreadyReviewed, RecommendationNotFound

__all__ = ["RecommendationPort", "RecommendationRepositoryPort"]


class RecommendationPort(ABC):
    """Outbound port: sessions in, traceable recommendations out."""

    @abstractmethod
    def generate(self, sessions: Sequence[SprintSession]) -> list[Recommendation]:
        """Apply the documented method to ``sessions``.

        Implementations must never claim causal or clinical effects and
        must return ``INSUFFICIENT_DATA`` instead of an unsupported
        suggestion when the input does not justify one.
        """


class RecommendationRepositoryPort(ABC):
    """Persistence port for generated and teacher-reviewed outputs."""

    @abstractmethod
    def save(self, recommendation: Recommendation, generated_by: int) -> Recommendation:
        """Insert a recommendation or return its existing idempotent record."""

    @abstractmethod
    def list_for_sessions(
        self,
        session_ids: Sequence[str],
        review_states: Optional[Sequence[ReviewState]] = None,
    ) -> list[Recommendation]:
        """Return records whose complete origin set is in ``session_ids``."""

    @abstractmethod
    def review(
        self,
        recommendation_id: str,
        review_state: ReviewState,
        reviewer_id: int,
        reviewed_at: datetime,
        note: Optional[str] = None,
    ) -> Recommendation:
        """Record a one-time teacher approval/rejection.

        Raises ``RecommendationNotFound`` or ``RecommendationAlreadyReviewed``.
        """

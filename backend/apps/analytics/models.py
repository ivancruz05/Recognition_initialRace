"""Django model discovery entry point for the analytics app."""

from .infrastructure.models import RecommendationRecord

__all__ = ["RecommendationRecord"]

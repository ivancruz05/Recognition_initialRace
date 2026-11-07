"""Driven adapters of the analytics module.

Only the recommendation port implementations live here (today the
documented rule set; tomorrow a model, without changing the domain or the
use cases).
"""

from .rule_based_recommendations import RuleBasedRecommendationAdapter
from .repositories import DjangoRecommendationRepository

__all__ = ["DjangoRecommendationRepository", "RuleBasedRecommendationAdapter"]

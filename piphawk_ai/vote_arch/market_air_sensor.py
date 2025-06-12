"""Calculate market air index used in prompts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketSnapshot:
    atr: float
    news_score: float
    oi_bias: float


def air_index(m: MarketSnapshot) -> float:
    vol_heat = min(m.atr / 0.1, 1)
    news_heat = min(abs(m.news_score) / 5, 1)
    flow_heat = abs(m.oi_bias)
    return 0.5 * vol_heat + 0.3 * news_heat + 0.2 * flow_heat

__all__ = ["MarketSnapshot", "air_index"]

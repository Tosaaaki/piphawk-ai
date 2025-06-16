"""Calculate market air index used in prompts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketSnapshot:
    atr: float
    news_score: float
    oi_bias: float


def air_index(m: MarketSnapshot) -> float:
    """Return market air index based solely on technical indicators."""
    vol_heat = min(m.atr / 0.1, 1)
    flow_heat = abs(m.oi_bias)
    # ニューススコアは一時的に無視する
    return 0.7 * vol_heat + 0.3 * flow_heat

__all__ = ["MarketSnapshot", "air_index"]

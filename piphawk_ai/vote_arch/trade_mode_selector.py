from __future__ import annotations

"""Trade mode selection with majority vote and rule fallback."""

from .ai_strategy_selector import select_strategy
from .regime_detector import MarketMetrics, rule_based_regime

_ALLOWED = {
    "micro_scalp",
    "scalp_momentum",
    "scalp_reversion",
    "trend_follow",
    "strong_trend",
}

_FALLBACK = {
    "trend": "trend_follow",
    "range": "scalp_momentum",
    "vol_spike": "scalp_reversion",
}


def select_mode(prompt: str, metrics: MarketMetrics) -> str:
    """Return final trade mode via majority vote with rule fallback."""
    mode, ok = select_strategy(prompt)
    if mode in _ALLOWED and ok:
        return mode
    regime = rule_based_regime(metrics)
    return _FALLBACK.get(regime, "scalp_momentum")


__all__ = ["select_mode"]

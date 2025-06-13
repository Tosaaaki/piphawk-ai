from __future__ import annotations
"""Simple trade mode detector without LLM."""

from .mode_preclassifier import classify_regime

# Map regime categories to trade modes
_REGIME_TO_MODE = {
    "trend": "trend_follow",
    "range": "scalp_momentum",
}


def detect_mode(features: dict) -> str:
    """Return trade mode based on preclassifier only."""
    regime = classify_regime(features)
    return _REGIME_TO_MODE.get(regime, "no_trade")

__all__ = ["detect_mode"]

"""Simple rule-based regime detection."""
from __future__ import annotations

from dataclasses import dataclass

from backend.utils import env_loader

@dataclass
class MarketMetrics:
    """Container for indicator values used in regime detection."""
    adx_m5: float
    ema_fast: float
    ema_slow: float
    bb_width_m5: float

REGIME_ADX_TREND = float(env_loader.get_env("REGIME_ADX_TREND", "30"))
REGIME_BB_NARROW = float(env_loader.get_env("REGIME_BB_NARROW", "0.05"))


def rule_based_regime(m: MarketMetrics) -> str:
    """Return market regime based on ADX and Bollinger width."""
    if m.adx_m5 >= REGIME_ADX_TREND and m.ema_fast > m.ema_slow:
        return "trend"
    if m.bb_width_m5 <= REGIME_BB_NARROW and m.adx_m5 < 20:
        return "range"
    return "vol_spike"

__all__ = ["MarketMetrics", "rule_based_regime"]

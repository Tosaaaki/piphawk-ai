"""
モード選択ロジック.
"""
from __future__ import annotations

from typing import Dict


def _norm(value: float, scale: float) -> float:
    """値を 0-1 に正規化."""
    if scale <= 0:
        return 0.0
    v = abs(value) / scale
    return min(max(v, 0.0), 1.0)


def select_mode(context: Dict[str, float]) -> str:
    """コンテキストからトレードモードを決定."""
    slope = context.get("ema_slope_15m", 0.0)
    adx = context.get("adx_15m", 0.0)
    overshoot = context.get("overshoot_flag", 0)

    slope_norm = _norm(slope, 0.3)
    adx_norm = _norm(adx, 50.0)
    trend_strength = slope_norm * adx_norm

    if trend_strength > 0.6:
        return "TREND"
    if overshoot:
        return "REBOUND_SCALP"
    return "BASE_SCALP"

__all__ = ["select_mode"]

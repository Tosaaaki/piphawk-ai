from __future__ import annotations

"""Volatility and breakout filter."""

from typing import List, Dict


def _last_val(series):
    try:
        if hasattr(series, "iloc"):
            return float(series.iloc[-1])
        return float(series[-1])
    except Exception:
        return None


def _series_list(series) -> List[float]:
    try:
        if hasattr(series, "_data"):
            return [float(v) for v in series._data]
        if hasattr(series, "tolist"):
            return [float(v) for v in series.tolist()]
        return [float(v) for v in series]
    except Exception:
        return []


def _ema_latest(series, span: int = 14) -> float | None:
    values = _series_list(series)
    if not values:
        return None
    alpha = 2 / (span + 1)
    ema = values[0]
    for v in values[1:]:
        ema = ema + alpha * (v - ema)
    return ema


def should_block_short(candles: List[Dict], atr_series) -> bool:
    """Return True when ATR spike with consecutive highs detected."""
    if len(candles) < 3 or atr_series is None:
        return False
    atr = _last_val(atr_series)
    ema = _ema_latest(atr_series)
    if atr is None or ema is None:
        return False
    if atr <= ema * 1.3:
        return False
    try:
        highs = []
        for c in candles[-3:]:
            base = c.get("mid", c)
            highs.append(float(base.get("h")))
        if highs[2] > highs[1] > highs[0]:
            return True
    except Exception:
        return False
    return False


__all__ = ["should_block_short"]

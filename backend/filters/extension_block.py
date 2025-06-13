from __future__ import annotations

"""Prevent entries when price is extended far from EMA."""

from typing import Dict, Sequence


def _ema(values: Sequence[float], period: int) -> float:
    """Return EMA of the given values."""
    if not values:
        return 0.0
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _atr(high: Sequence[float], low: Sequence[float], close: Sequence[float], period: int) -> float:
    """Return ATR using the classic formula."""
    if len(high) < period or len(low) < period or len(close) < period:
        return 0.0
    trs = []
    for i in range(1, period + 1):
        hl = high[-i] - low[-i]
        hc = abs(high[-i] - close[-i - 1]) if i < len(close) else hl
        lc = abs(low[-i] - close[-i - 1]) if i < len(close) else hl
        trs.append(max(hl, hc, lc))
    return sum(trs) / period


def _val(candle: Dict, key: str) -> float:
    base = candle.get("mid", candle)
    return float(base.get(key))


def is_extension(candles: Sequence[Dict], atr: float) -> bool:
    """最新足の実体が ATR×3 を超えていれば True."""
    if atr <= 0 or not candles:
        return False

    last = candles[-1]
    open_v = _val(last, "o")
    close_v = _val(last, "c")
    body = abs(close_v - open_v)
    return body > atr * 3

__all__ = ["is_extension"]

from __future__ import annotations

"""Prevent entries when price is extended far from EMA."""

from typing import Sequence, Dict

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


def extension_block(candles: Sequence[Dict], ratio: float) -> bool:
    """Return ``True`` if the latest close deviates from EMA20 by ``ratio``×ATR."""
    if ratio <= 0 or len(candles) < 20:
        return False

    closes = [_val(c, "c") for c in candles[-20:]]
    highs = [_val(c, "h") for c in candles[-14:]]
    lows = [_val(c, "l") for c in candles[-14:]]

    ema20 = _ema(closes[-20:], 20)
    atr_val = _atr(highs, lows, closes, 14)
    latest = closes[-1]

    return abs(latest - ema20) >= ratio * atr_val

__all__ = ["extension_block"]

"""False breakout detection utilities."""
from __future__ import annotations
from typing import Sequence


def is_false_breakout(candles: Sequence[dict], lookback: int = 20) -> bool:
    """Return True if a breakout candle is followed by a close back inside range."""
    if len(candles) < lookback + 2:
        return False
    prev = candles[-2]
    last = candles[-1]
    recent = [c for c in candles[-(lookback + 2):-2] if c.get("complete", True)]
    if not recent:
        return False
    highs = [float(c["mid"]["h"]) for c in recent]
    lows = [float(c["mid"]["l"]) for c in recent]
    range_high = max(highs)
    range_low = min(lows)
    prev_close = float(prev["mid"]["c"])
    last_close = float(last["mid"]["c"])
    if prev_close > range_high and last_close <= range_high:
        return True
    if prev_close < range_low and last_close >= range_low:
        return True
    return False

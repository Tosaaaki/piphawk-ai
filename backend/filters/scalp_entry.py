"""ADX・EMA を使わない簡素なスキャルプフィルター."""
from __future__ import annotations

from typing import Dict, List


def _val(candle: Dict, key: str) -> float:
    base = candle.get("mid", candle)
    return float(base.get(key))




def should_enter_long(candles: List[Dict], indicators: dict) -> bool:
    """Return True if scalping long conditions are met."""
    if not candles:
        return False
    last_close = _val(candles[-1], "c")
    last_open = _val(candles[-1], "o")
    return last_close > last_open


def should_enter_short(candles: List[Dict], indicators: dict) -> bool:
    """Return True if scalping short conditions are met."""
    if not candles:
        return False
    last_close = _val(candles[-1], "c")
    last_open = _val(candles[-1], "o")
    return last_close < last_open


__all__ = ["should_enter_long", "should_enter_short"]

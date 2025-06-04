"""Breakout entry filter."""

from typing import List, Dict
from backend.utils import env_loader


def _get_val(candle: Dict, key: str) -> float:
    """Return float value from candle or its 'mid' subdict."""
    base = candle.get("mid", candle)
    return float(base.get(key))


def _last_val(series):
    if series is None:
        return None
    try:
        if hasattr(series, "iloc"):
            return float(series.iloc[-1])
        if isinstance(series, (list, tuple)):
            return float(series[-1])
        return float(series)
    except Exception:
        return None


def should_enter_breakout(candles: List[Dict], indicators: Dict) -> bool:
    """Return True when ADX is high and latest close breaks previous high/low."""
    if len(candles) < 2:
        return False

    adx_val = _last_val(indicators.get("adx"))
    if adx_val is None:
        return False

    adx_thresh = float(env_loader.get_env("BREAKOUT_ADX_MIN", "30"))
    if adx_val < adx_thresh:
        return False

    last = candles[-1]
    prev = candles[-2]
    last_close = _get_val(last, "c")
    prev_high = _get_val(prev, "h")
    prev_low = _get_val(prev, "l")

    return last_close > prev_high or last_close < prev_low

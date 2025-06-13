"""スキャルプ用エントリーフィルター."""
from __future__ import annotations

from typing import Dict, List

from backend.utils import env_loader


def _val(candle: Dict, key: str) -> float:
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


def should_enter_long(candles: List[Dict], indicators: dict) -> bool:
    """Return True if scalping long conditions are met."""
    if not candles:
        return False
    adx_val = _last_val(indicators.get("adx"))
    ema_fast = _last_val(indicators.get("ema_fast"))
    ema_slow = _last_val(indicators.get("ema_slow"))
    if adx_val is None or ema_fast is None or ema_slow is None:
        return False
    adx_min = float(env_loader.get_env("SCALP_ADX_MIN", "15"))
    if adx_val < adx_min or ema_fast <= ema_slow:
        return False
    last_close = _val(candles[-1], "c")
    last_open = _val(candles[-1], "o")
    return last_close > last_open


def should_enter_short(candles: List[Dict], indicators: dict) -> bool:
    """Return True if scalping short conditions are met."""
    if not candles:
        return False
    adx_val = _last_val(indicators.get("adx"))
    ema_fast = _last_val(indicators.get("ema_fast"))
    ema_slow = _last_val(indicators.get("ema_slow"))
    if adx_val is None or ema_fast is None or ema_slow is None:
        return False
    adx_min = float(env_loader.get_env("SCALP_ADX_MIN", "15"))
    if adx_val < adx_min or ema_fast >= ema_slow:
        return False
    last_close = _val(candles[-1], "c")
    last_open = _val(candles[-1], "o")
    return last_close < last_open


__all__ = ["should_enter_long", "should_enter_short"]

"""Trend pullback entry filter."""

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


def should_enter_long(candles: List[Dict], indicators: dict) -> bool:
    """Return True if long pullback conditions are met."""
    if len(candles) < 2:
        return False

    adx_val = _last_val(indicators.get("adx"))
    ema_fast = _last_val(indicators.get("ema_fast"))
    ema_slow = _last_val(indicators.get("ema_slow"))
    atr_val = _last_val(indicators.get("atr"))

    if adx_val is None or ema_fast is None or ema_slow is None or atr_val is None:
        return False

    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    adx_thresh = float(env_loader.get_env("TREND_PB_ADX", "25"))
    min_atr_pips = float(env_loader.get_env("TREND_PB_MIN_ATR_PIPS", "0"))

    # --- ADX と ATR によるフィルタ ---
    if adx_val < adx_thresh or atr_val / pip_size < min_atr_pips:
        return False

    # --- EMA の並びを確認し上昇トレンドかを判断 ---
    if ema_fast <= ema_slow:
        return False

    last = candles[-1]
    prev = candles[-2]
    last_open = _get_val(last, "o")
    last_close = _get_val(last, "c")
    last_low = _get_val(last, "l")
    prev_open = _get_val(prev, "o")
    prev_close = _get_val(prev, "c")

    # --- 押し目形成を確認（前足陰線 → 最新足陽線） ---
    if prev_close >= prev_open or last_close <= last_open:
        return False

    # --- EMA 付近から反発しているか判定 ---
    if last_low > ema_fast and last_low > ema_slow:
        return False

    return True

"""Trend pullback entry filter."""

from typing import List, Dict, Sequence
from backend.utils import env_loader


def _get_val(candle: Dict, key: str) -> float:
    """Return float value from candle or its 'mid' subdict."""
    base = candle.get("mid", candle)
    return float(base.get(key))


def _ema(values: Sequence[float], period: int) -> float:
    """Simple EMA calculation used for deviation checks."""
    if not values:
        return 0.0
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


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


def should_enter_short(candles: List[Dict], indicators: dict) -> bool:
    """Return True if short pullback conditions are met."""
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

    # --- EMA の並びを確認し下降トレンドかを判断 ---
    if ema_fast >= ema_slow:
        return False

    last = candles[-1]
    prev = candles[-2]
    last_open = _get_val(last, "o")
    last_close = _get_val(last, "c")
    last_high = _get_val(last, "h")
    prev_open = _get_val(prev, "o")
    prev_close = _get_val(prev, "c")

    # --- 戻り形成を確認（前足陽線 → 最新足陰線） ---
    if prev_close <= prev_open or last_close >= last_open:
        return False

    # --- EMA 付近から反落しているか判定 ---
    if last_high < ema_fast and last_high < ema_slow:
        return False

    return True


def should_skip(candles: List[Dict], ema_period: int = 20) -> bool:
    """EMA乖離からの強い戻しがあればエントリーを避ける."""
    if len(candles) < ema_period + 1:
        return False

    closes = [_get_val(c, "c") for c in candles[-(ema_period + 1) :]]
    ema_val = _ema(closes[:-1], ema_period)
    if not ema_val:
        return False

    last = candles[-1]
    open_v = _get_val(last, "o")
    close_v = _get_val(last, "c")
    dev = abs(open_v - ema_val) / ema_val
    if dev > 0.01 and ((open_v > ema_val and close_v < ema_val) or (open_v < ema_val and close_v > ema_val)):
        return True

    return False


__all__ = ["should_enter_long", "should_enter_short", "should_skip"]

"""ADX や EMA を参照しない単純なプルバックフィルター."""

from typing import Dict, List, Sequence


def _get_val(candle: Dict, key: str) -> float:
    """Return float value from candle or its 'mid' subdict."""
    base = candle.get("mid", candle)
    return float(base.get(key))





def should_enter_long(candles: List[Dict], indicators: dict) -> bool:
    """Return True if long pullback conditions are met."""
    if len(candles) < 2:
        return False


    last = candles[-1]
    prev = candles[-2]
    last_open = _get_val(last, "o")
    last_close = _get_val(last, "c")
    prev_open = _get_val(prev, "o")
    prev_close = _get_val(prev, "c")

    # --- 押し目形成を確認（前足陰線 → 最新足陽線） ---
    if prev_close >= prev_open or last_close <= last_open:
        return False

    return True


def should_enter_short(candles: List[Dict], indicators: dict) -> bool:
    """Return True if short pullback conditions are met."""
    if len(candles) < 2:
        return False

    last = candles[-1]
    prev = candles[-2]
    last_open = _get_val(last, "o")
    last_close = _get_val(last, "c")
    prev_open = _get_val(prev, "o")
    prev_close = _get_val(prev, "c")

    # --- 戻り形成を確認（前足陽線 → 最新足陰線） ---
    if prev_close <= prev_open or last_close >= last_open:
        return False

    return True


def should_skip(candles: List[Dict], ema_period: int = 20) -> bool:
    """Return True when price is overextended from EMA."""

    if len(candles) < ema_period + 1:
        return False

    closes = [_get_val(c, "c") for c in candles[-(ema_period + 1) : -1]]
    ema = sum(closes) / len(closes)
    last = _get_val(candles[-1], "c")
    prev = _get_val(candles[-2], "c")
    if last > ema and prev > ema:
        return True
    if last < ema and prev < ema:
        return True
    return False


__all__ = ["should_enter_long", "should_enter_short", "should_skip"]

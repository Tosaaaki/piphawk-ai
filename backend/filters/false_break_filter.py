"""False break detection filter."""

from typing import List, Dict


def _get_val(candle: Dict, key: str) -> float:
    base = candle.get("mid", candle)
    return float(base.get(key))


def should_skip(candles: List[Dict], lookback: int, threshold_ratio: float) -> bool:
    """Return True if the latest candle forms a reversal wick near swing high/low."""
    if len(candles) < lookback + 1:
        return False
    try:
        recent = candles[-(lookback + 1):-1]
        high_vals = [_get_val(c, "h") for c in recent]
        low_vals = [_get_val(c, "l") for c in recent]
        swing_high = max(high_vals)
        swing_low = min(low_vals)

        last = candles[-1]
        high = _get_val(last, "h")
        low = _get_val(last, "l")
        open_v = _get_val(last, "o")
        close_v = _get_val(last, "c")
        rng = high - low
        if rng <= 0:
            return False

        # 上方向へのダマシブレイク判定
        upper_wick = high - max(open_v, close_v)
        if (
            high >= swing_high
            and close_v < open_v
            and upper_wick / rng >= threshold_ratio
        ):
            return True

        # 下方向へのダマシブレイク判定
        lower_wick = min(open_v, close_v) - low
        if (
            low <= swing_low
            and close_v > open_v
            and lower_wick / rng >= threshold_ratio
        ):
            return True
    except Exception:
        return False

    return False

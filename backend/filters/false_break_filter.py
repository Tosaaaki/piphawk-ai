"""False break detection filter."""

from typing import List, Dict


def _get_val(candle: Dict, key: str) -> float:
    base = candle.get("mid", candle)
    return float(base.get(key))


def should_skip(candles: List[Dict], lookback: int = 3) -> bool:
    """直近レンジから 50% 以上戻したらエントリーをスキップする."""
    if len(candles) < lookback + 1:
        return False

    try:
        recent = candles[-(lookback + 1) : -1]
        highs = [_get_val(c, "h") for c in recent]
        lows = [_get_val(c, "l") for c in recent]
        high_max = max(highs)
        low_min = min(lows)
        rng = high_max - low_min
        if rng <= 0:
            return False

        last = candles[-1]
        close_v = _get_val(last, "c")
        if _get_val(last, "h") > high_max and close_v <= high_max - rng * 0.5:
            return True
        if _get_val(last, "l") < low_min and close_v >= low_min + rng * 0.5:
            return True
    except Exception:
        return False

    return False

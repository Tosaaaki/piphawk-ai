try:
    import pandas as pd  # noqa: F401
except ImportError:
    pass

from typing import Sequence, Optional


def compute_volume_sma(volumes: Sequence[float], period: int) -> Optional[float]:
    """Return simple moving average of volumes."""
    if period <= 0:
        return None
    vals = []
    for v in volumes:
        try:
            vals.append(float(v))
        except Exception:
            continue
    if len(vals) < period:
        return None
    return sum(vals[-period:]) / period


def get_candle_features(candle: dict, *, volume_sma: Optional[float] = None) -> dict:
    """Return candle tail ratio and volume spike flag."""
    try:
        mid = candle.get("mid", {})
        open_p = float(mid.get("o", candle.get("o")))
        close_p = float(mid.get("c", candle.get("c")))
        high_p = float(mid.get("h", candle.get("h")))
        low_p = float(mid.get("l", candle.get("l")))
    except Exception:
        return {"tail_ratio": 0.0, "vol_spike": False}

    body = abs(close_p - open_p)
    upper = high_p - max(open_p, close_p)
    lower = min(open_p, close_p) - low_p
    tail_ratio = float("inf") if body == 0 else max(upper, lower) / body

    vol_spike = False
    vol = candle.get("volume")
    if volume_sma is not None and vol is not None:
        try:
            vol_spike = float(vol) > 1.5 * volume_sma
        except Exception:
            vol_spike = False
    return {"tail_ratio": tail_ratio, "vol_spike": vol_spike}

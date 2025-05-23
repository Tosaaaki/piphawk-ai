from __future__ import annotations

from typing import List, Dict, Optional


def detect_range_break(candles: List[dict], *, lookback: int = 20, pivot: Optional[float] = None) -> Dict[str, Optional[str]]:
    """Detect if the latest candle closed outside the recent range.

    Parameters
    ----------
    candles : List of candle dicts with `mid` prices.
    lookback : How many previous candles define the range.
    pivot : Optional pivot level that must also be broken.

    Returns
    -------
    dict
        {{"break": bool, "direction": "up"|"down"|None}}
    """
    if not candles or len(candles) <= lookback:
        return {"break": False, "direction": None}

    recent = [c for c in candles[-(lookback + 1):-1] if c.get("complete", True)]
    last = candles[-1]
    if not recent or "mid" not in last:
        return {"break": False, "direction": None}

    highs = [float(c["mid"]["h"]) for c in recent]
    lows = [float(c["mid"]["l"]) for c in recent]
    last_close = float(last["mid"]["c"])

    range_high = max(highs)
    range_low = min(lows)

    direction: Optional[str] = None
    if last_close > range_high and (pivot is None or last_close > pivot):
        direction = "up"
    elif last_close < range_low and (pivot is None or last_close < pivot):
        direction = "down"

    return {"break": direction is not None, "direction": direction}


def classify_breakout(indicators: dict, adx_thresh: float = 25.0, ema_thresh: float = 0.05) -> Optional[str]:
    """Classify breakout continuation as trend or range."""
    adx_series = indicators.get("adx")
    ema_series = indicators.get("ema_slope")

    def _last_val(series):
        if series is None:
            return None
        try:
            return float(series.iloc[-1]) if hasattr(series, "iloc") else float(series[-1])
        except Exception:
            return None

    adx_val = _last_val(adx_series)
    ema_val = _last_val(ema_series)

    if adx_val is None or ema_val is None:
        return None

    if adx_val >= adx_thresh and abs(ema_val) >= ema_thresh:
        return "trend"
    return "range"

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
    if not recent or "mid" not in last or not last.get("complete", True):
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


def detect_atr_breakout(
    candles: List[dict],
    atr_series,
    lookback: int = 20,
    mult: float = 0.5,
) -> Optional[str]:
    """ATR に基づくブレイクアウト判定を行う。

    直近 ``lookback`` 本の高値・安値から最高値・最安値を求め、
    ATR の最新値に ``mult`` を掛けた値を閾値として終値が上抜け・下抜け
    した場合に ``"up"`` もしくは ``"down"`` を返す。
    """

    if not candles or len(candles) < lookback + 1 or atr_series is None:
        return None

    try:
        if hasattr(atr_series, "iloc"):
            atr_val = float(atr_series.iloc[-1])
        else:
            atr_val = float(atr_series[-1])
    except Exception:
        return None

    threshold = atr_val * mult

    recent = [c for c in candles[-(lookback + 1):-1] if c.get("complete", True)]
    last = candles[-1]
    if not recent or "mid" not in last:
        return None

    highs = [float(c["mid"]["h"]) for c in recent]
    lows = [float(c["mid"]["l"]) for c in recent]
    last_close = float(last["mid"]["c"])

    range_high = max(highs)
    range_low = min(lows)

    if last_close > range_high + threshold:
        return "up"
    if last_close < range_low - threshold:
        return "down"
    return None



"""
higher_tf_analysis.py

Utility for extracting higher‑timeframe reference levels (D, H4, etc.)
so that short‑term strategies can be made “context‑aware”.

Returned levels are *pure data*; interpretation is delegated to
filters / AI prompts.

Example usage (JobRunner):
    from backend.strategy.higher_tf_analysis import analyze_higher_tf
    higher_tf = analyze_higher_tf("USD_JPY")
"""

from __future__ import annotations

import logging
from statistics import mean
from typing import Dict, List, Tuple, Union

import pandas as pd

from backend.market_data.candle_fetcher import fetch_candles

logger = logging.getLogger(__name__)


def _pivot(high: float, low: float, close: float) -> float:
    """Classic floor‑trader pivot."""
    return (high + low + close) / 3.0


def _sma(values: List[float], period: int) -> Union[float, None]:
    """Simple moving average with graceful fallback when length < period."""
    if len(values) < period:
        return None
    return mean(values[-period:])


def analyze_higher_tf(pair: str, *, day_lookback: int = 200, h4_lookback: int = 90) -> Dict[str, float]:
    """
    Fetch higher‑timeframe candles and compute key reference levels.

    Args:
        pair: Instrument code, e.g. "USD_JPY".
        day_lookback: How many daily candles to pull (for SMA200).
        h4_lookback: How many H4 candles to pull (~15 days).

    Returns:
        Dict[str, float] where missing values are set to None.
    """
    try:
        # --- Daily (D) ----------------------------------------------------
        daily_candles = fetch_candles(pair, granularity="D", count=day_lookback)
        if not daily_candles:
            logger.warning("No daily candles fetched for %s", pair)
            return {}

        # last completed D candle
        last_d = daily_candles[-1] if daily_candles[-1]["complete"] else daily_candles[-2]
        day_high = float(last_d["mid"]["h"])
        day_low = float(last_d["mid"]["l"])
        day_close = float(last_d["mid"]["c"])
        pivot_d = _pivot(day_high, day_low, day_close)

        close_d = [float(c["mid"]["c"]) for c in daily_candles if c["complete"]]
        sma50_d = _sma(close_d, 50)
        sma200_d = _sma(close_d, 200)

        # --- H4 -----------------------------------------------------------
        h4_candles = fetch_candles(pair, granularity="H4", count=h4_lookback)
        recent_high = (
            max(float(c["mid"]["h"]) for c in h4_candles if c["complete"])
            if h4_candles
            else None
        )
        recent_low = (
            min(float(c["mid"]["l"]) for c in h4_candles if c["complete"])
            if h4_candles
            else None
        )

        return {
            "day_high": day_high,
            "day_low": day_low,
            "pivot_d": pivot_d,
            "sma50_d": sma50_d,
            "sma200_d": sma200_d,
            "h4_recent_high": recent_high,
            "h4_recent_low": recent_low,
        }

    except Exception as exc:
        logger.error("Error in higher_tf_analysis: %s", exc, exc_info=True)
        return {}
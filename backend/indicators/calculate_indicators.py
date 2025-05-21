import os
from typing import Sequence

import numpy as np
import pandas as pd

from backend.indicators.rsi import calculate_rsi
from backend.indicators.ema import calculate_ema
from backend.indicators.atr import calculate_atr
from backend.indicators.bollinger import calculate_bollinger_bands
from backend.indicators.adx import calculate_adx
from backend.market_data.candle_fetcher import fetch_candles


def _percentile_rank(series: Sequence[float], value: float) -> float | None:
    """Return percentile rank of ``value`` within ``series`` (0-100)."""
    if not series:
        return None
    arr = pd.Series(series).dropna().to_numpy()
    if arr.size == 0:
        return None
    rank = np.searchsorted(np.sort(arr), value, side="right")
    return 100.0 * rank / arr.size

def calculate_indicators(
    market_data,
    *,
    pair: str | None = None,
    history_days: int = 90,
) -> dict:
    """Calculate trading indicators and recent-percentile stats."""
    close_prices = [float(candle['mid']['c']) for candle in market_data if candle['complete']]
    high_prices = [float(candle['mid']['h']) for candle in market_data if candle['complete']]
    low_prices = [float(candle['mid']['l']) for candle in market_data if candle['complete']]

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Latest close prices: {close_prices[-15:]}")

    ema_fast_period = int(os.getenv("EMA_FAST_PERIOD", "9"))
    ema_slow_period = int(os.getenv("EMA_SLOW_PERIOD", "21"))

    # --- Bollinger Bands (DataFrame) ---
    bb_df = calculate_bollinger_bands(close_prices)

    # --- ADX (trend strength) ---
    adx_series = calculate_adx(high_prices, low_prices, close_prices)

    indicators = {
        'rsi': calculate_rsi(close_prices),
        'ema_fast': calculate_ema(close_prices, period=ema_fast_period),
        'ema_slow': calculate_ema(close_prices, period=ema_slow_period),
        'atr': calculate_atr(high_prices, low_prices, close_prices),
        # Spread Bollinger components so filters can access them directly
        'bb_upper': bb_df['upper_band'],
        'bb_lower': bb_df['lower_band'],
        'bb_middle': bb_df['middle_band'],
        'adx': adx_series,
    }

    # --- Percentile stats from historical daily data --------------------
    if pair is None:
        pair = os.getenv("DEFAULT_PAIR")
    try:
        history = fetch_candles(pair, granularity="D", count=history_days)
    except Exception:
        history = []

    if history:
        h_close = [float(c['mid']['c']) for c in history if c.get('complete')]
        h_high = [float(c['mid']['h']) for c in history if c.get('complete')]
        h_low = [float(c['mid']['l']) for c in history if c.get('complete')]

        hist_bb = calculate_bollinger_bands(h_close)
        hist_bb_width = (hist_bb['upper_band'] - hist_bb['lower_band']).tolist()
        hist_atr = calculate_atr(h_high, h_low, h_close).tolist()

        current_bb_width = (
            indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1]
        )
        current_atr = indicators['atr'].iloc[-1]

        indicators['bb_width_pct'] = _percentile_rank(hist_bb_width, current_bb_width)
        indicators['atr_pct'] = _percentile_rank(hist_atr, current_atr)
    else:
        indicators['bb_width_pct'] = None
        indicators['atr_pct'] = None

    return indicators


def calculate_indicators_multi(candles_dict: dict[str, list]) -> dict:
    """Calculate indicators for multiple timeframes.

    Parameters
    ----------
    candles_dict : dict[str, list]
        Dictionary mapping timeframe strings (e.g. "M1", "M5", "D") to candle
        lists.

    Returns
    -------
    dict
        Dictionary mapping each timeframe to its indicators dictionary.
    """
    results: dict[str, dict] = {}
    for tf, candles in candles_dict.items():
        results[tf] = calculate_indicators(candles)
    return results

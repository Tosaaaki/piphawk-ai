

from __future__ import annotations

"""
Average Directional Movement Index (ADX) implementation.

This indicator measures trend strength on a scale of 0‑100.
Typical interpretation:
    ADX < 20‑25 : ranging / weak trend
    ADX > 25‑30 : trending market

Usage:
    from backend.indicators.adx import calculate_adx
    adx_series = calculate_adx(high, low, close, period=14)
"""

from typing import Sequence

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e

def calculate_adx(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    period: int = 14
) -> pd.Series:
    """
    Compute the ADX for given high/low/close series.

    Args:
        high, low, close : list‑like price series (same length).
        period           : look‑back length (default 14).

    Returns:
        pd.Series of ADX values (NaN for the first <period>*2 rows).
    """
    high = pd.Series(high, dtype="float64")
    low = pd.Series(low, dtype="float64")
    close = pd.Series(close, dtype="float64")

    # 1. True Range (TR)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)

    # 2. Directional Movements
    up  = high.diff()
    down = -low.diff()
    plus_dm  = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)

    # 3. Smoothed values (Wilder's smoothing)
    atr = tr.rolling(period).mean()
    plus_di  = 100 * (plus_dm.rolling(period).sum() / atr)
    minus_di = 100 * (minus_dm.rolling(period).sum() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()

    return adx


def calculate_di(
    high: Sequence[float],
    low: Sequence[float],
    close: Sequence[float],
    period: int = 14,
) -> tuple[pd.Series, pd.Series]:
    """Return +DI and -DI series using Wilder's smoothing."""

    high = pd.Series(high, dtype="float64")
    low = pd.Series(low, dtype="float64")
    close = pd.Series(close, dtype="float64")

    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
        axis=1,
    ).max(axis=1)

    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)

    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).sum() / atr)
    minus_di = 100 * (minus_dm.rolling(period).sum() / atr)

    return plus_di, minus_di


def calculate_adx_slope(adx_values: Sequence[float], lookback: int = 5) -> float:
    """Return slope of the last ``lookback`` ADX values using linear regression."""

    try:
        vals = [float(v) for v in adx_values if v is not None]
    except Exception:
        return 0.0

    if len(vals) < lookback:
        return 0.0

    y = vals[-lookback:]
    n = len(y)
    if n <= 1:
        return 0.0

    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    den = sum((xi - x_mean) ** 2 for xi in x)
    if den == 0:
        return 0.0

    slope = num / den
    return float(slope)


def calculate_adx_bb_score(
    adx: Sequence[float],
    bb_upper: Sequence[float],
    bb_lower: Sequence[float],
    lookback: int = 3,
    width_period: int = 20,
) -> float:
    """Return composite score from ADX change and Bollinger Band width."""
    try:
        adx_vals = [float(v) for v in adx]
        up_vals = [float(v) for v in bb_upper]
        low_vals = [float(v) for v in bb_lower]
    except Exception:
        return 0.0

    if len(adx_vals) <= lookback or len(up_vals) < width_period or len(low_vals) < width_period:
        return 0.0

    adx_delta = adx_vals[-1] - adx_vals[-lookback]
    cur_width = up_vals[-1] - low_vals[-1]
    widths = [u - l for u, l in zip(up_vals[-width_period:], low_vals[-width_period:])]
    avg_width = sum(widths) / len(widths) if widths else 0.0
    if avg_width == 0:
        return 0.0
    width_ratio = cur_width / avg_width

    return float(adx_delta * width_ratio)


__all__ = [
    "calculate_adx",
    "calculate_di",
    "calculate_adx_slope",
    "calculate_adx_bb_score",
]

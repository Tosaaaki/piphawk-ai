from __future__ import annotations

"""Bollinger Band utilities for multiple timeframes."""

from typing import Sequence, Mapping, Dict
import os

try:
    import pandas as pd
except ImportError as e:  # pragma: no cover - dependency guard
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e


def _calc_single(prices: Sequence[float], window: int = 20, num_std: float = 2.0) -> Dict[str, float]:
    """Return latest Bollinger values as a dict."""
    series = pd.Series(prices)
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    if ma.empty:
        return {"middle": 0.0, "upper": 0.0, "lower": 0.0}
    middle = ma.iloc[-1]
    sd = std.iloc[-1]
    return {"middle": middle, "upper": middle + num_std * sd, "lower": middle - num_std * sd}


def multi_bollinger(
    data: Mapping[str, Sequence[float]],
    *,
    window: int = 20,
    num_std: float = 2.0,
) -> Dict[str, Dict[str, float]]:
    """Calculate Bollinger bands for each timeframe in ``data``."""
    result: Dict[str, Dict[str, float]] = {}
    for tf, prices in data.items():
        result[tf] = _calc_single(prices, window=window, num_std=num_std)
    return result


def calculate_bollinger_bands(
    prices: Sequence[float],
    window: int | None = None,
    num_std: float | None = None,
) -> pd.DataFrame:
    """Return Bollinger Bands for ``prices`` as a DataFrame."""
    if window is None:
        window = int(os.environ.get("BOLLINGER_WINDOW", 20))
    if num_std is None:
        try:
            num_std = float(os.environ.get("BOLLINGER_STD", 2))
        except ValueError:
            num_std = 2.0
    series = pd.Series(prices)
    ma = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return pd.DataFrame({
        "middle_band": ma,
        "upper_band": upper,
        "lower_band": lower,
    })


def calculate_bb_width(
    prices: Sequence[float],
    window: int | None = None,
    num_std: float | None = None,
) -> pd.Series:
    """Return Bollinger Band width as a Series."""
    df = calculate_bollinger_bands(prices, window=window, num_std=num_std)
    return df["upper_band"] - df["lower_band"]


def close_breaks_bbands(prices: Sequence[float], level: float, window: int = 20) -> bool:
    """Return ``True`` if close price breaks the Bollinger band."""
    if len(prices) < window + 1:
        return False
    prev_bands = _calc_single(prices[:-1], window=window, num_std=level)
    last_bands = _calc_single(prices, window=window, num_std=level)
    prev_close = float(prices[-2])
    last_close = float(prices[-1])
    prev_out = prev_close > prev_bands["upper"] or prev_close < prev_bands["lower"]
    last_out = last_close > last_bands["upper"] or last_close < last_bands["lower"]
    return last_out and not prev_out


def high_hits_bbands(price_series, level: float, window: int = 20) -> bool:
    """Return ``True`` if high or low touches the Bollinger band."""
    df = pd.DataFrame(price_series)
    if df.empty or not {"high", "low", "close"}.issubset(df.columns):
        return False
    if len(df) < window:
        return False
    bands = _calc_single(df["close"], window=window, num_std=level)
    high_val = float(df["high"].iloc[-1])
    low_val = float(df["low"].iloc[-1])
    return high_val >= bands["upper"] or low_val <= bands["lower"]


__all__ = [
    "multi_bollinger",
    "calculate_bollinger_bands",
    "calculate_bb_width",
    "close_breaks_bbands",
    "high_hits_bbands",
]


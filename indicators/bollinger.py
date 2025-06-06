from __future__ import annotations

"""Bollinger Band utilities for multiple timeframes."""

from typing import Sequence, Mapping, Dict

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


__all__ = ["multi_bollinger"]


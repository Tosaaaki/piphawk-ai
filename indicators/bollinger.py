from __future__ import annotations

"""Bollinger Band utilities for multiple timeframes."""

from typing import Dict, Mapping, Sequence

from backend.indicators.bollinger import calculate_bollinger_bands


def _calc_single(prices: Sequence[float], window: int = 20, num_std: float = 2.0) -> Dict[str, float]:
    """Return latest Bollinger values as a dict."""
    df = calculate_bollinger_bands(prices, window=window, num_std=num_std)
    if df.empty:
        return {"middle": 0.0, "upper": 0.0, "lower": 0.0}
    latest = df.iloc[-1]
    return {
        "middle": float(latest["middle_band"]),
        "upper": float(latest["upper_band"]),
        "lower": float(latest["lower_band"]),
    }


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


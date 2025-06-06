from __future__ import annotations

"""Utility functions for volatility measurements."""

from typing import Sequence


def candle_ranges(highs: Sequence[float], lows: Sequence[float]) -> list[float]:
    """Return high-low range for each candle."""
    return [h - l for h, l in zip(highs, lows)]


def band_width(upper: Sequence[float], lower: Sequence[float]) -> list[float]:
    """Return Bollinger band width for each value."""
    return [u - l for u, l in zip(upper, lower)]


__all__ = ["candle_ranges", "band_width"]


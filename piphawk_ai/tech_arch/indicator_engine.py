from __future__ import annotations

"""Indicator calculation helpers."""

from backend.indicators.calculate_indicators import calculate_indicators


def compute(candles: list[dict]) -> dict:
    """Return indicator dictionary for given candles."""
    return calculate_indicators(candles)


__all__ = ["compute"]

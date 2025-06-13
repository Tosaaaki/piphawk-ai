from __future__ import annotations

"""Wrapper around detect_mode for the technical pipeline."""

from analysis.detect_mode import detect_mode as _detect


def detect_mode(indicators: dict, candles: list[dict]) -> str:
    """Return trade mode string."""
    ctx = _detect(indicators, candles)
    return ctx.mode


__all__ = ["detect_mode"]

from __future__ import annotations

"""Simple market classification utilities."""

import logging

from backend.utils import env_loader

logger = logging.getLogger(__name__)


def _last(series):
    if series is None:
        return None
    try:
        if hasattr(series, "iloc"):
            return float(series.iloc[-1]) if len(series) else None
        if isinstance(series, (list, tuple)):
            return float(series[-1]) if series else None
        return float(series)
    except Exception:
        return None


def classify_market(indicators: dict) -> str:
    """Return 'trend' or 'range' based on ADX and EMA divergence."""
    adx = _last(indicators.get("adx"))
    ema_fast = _last(indicators.get("ema_fast"))
    ema_slow = _last(indicators.get("ema_slow"))

    if None in (adx, ema_fast, ema_slow):
        logger.debug("Insufficient indicators for classification")
        return "range"

    adx_min = float(env_loader.get_env("ADX_TREND_MIN", "25"))
    ema_diff_min = float(env_loader.get_env("EMA_DIFF_MIN", "0.001"))

    if adx >= adx_min and abs(ema_fast - ema_slow) >= ema_diff_min:
        return "trend"
    return "range"


__all__ = ["classify_market"]

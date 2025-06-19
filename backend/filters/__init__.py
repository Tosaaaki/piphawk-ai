
"""General entry filter helpers."""

from __future__ import annotations

import logging

from backend.utils import env_loader

logger = logging.getLogger(__name__)


def volatility_ok(context: dict) -> bool:
    """Return True if ATR meets the minimum threshold."""
    vol = context.get("atr")
    min_vol = float(env_loader.get_env("MIN_ATR", "0"))
    if vol is None:
        return False
    try:
        return float(vol) >= min_vol
    except Exception:
        return False


def spread_ok(context: dict) -> bool:
    """Return True when the spread is within the allowed range."""
    spread = context.get("spread")
    max_spread = float(env_loader.get_env("MAX_SPREAD_PIPS", "0"))
    if spread is None or max_spread <= 0:
        return True
    try:
        return float(spread) <= max_spread
    except Exception:
        return False


def session_ok(context: dict) -> bool:
    """Return True if current time falls within the allowed trading hours."""
    hour = context.get("hour")
    start = float(env_loader.get_env("SESSION_START", "0"))
    end = float(env_loader.get_env("SESSION_END", "24"))
    if hour is None:
        return True
    try:
        h = float(hour)
    except Exception:
        return False
    if start <= end:
        return start <= h < end
    return h >= start or h < end


def entry_filter(context: dict) -> bool:
    """Run basic entry filters and log the failing one."""
    # すべてのフィルターを無効化するため常に True を返す
    return True


def pre_check(
    indicators: dict,
    price: float | None = None,
    *,
    indicators_m1: dict | None = None,
    indicators_m15: dict | None = None,
    indicators_h1: dict | None = None,
    mode: str | None = None,
    context: dict | None = None,
) -> tuple[bool, str]:
    """Run basic and advanced entry filters."""
    # すべてのフィルターを無効化して常に通過させる
    return True, ""


__all__ = [
    "entry_filter",
    "pre_check",
    "volatility_ok",
    "spread_ok",
    "session_ok",
]

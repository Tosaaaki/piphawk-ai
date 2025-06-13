from __future__ import annotations

"""Prefilter utilities for the technical pipeline."""

from backend.utils import env_loader


def generic_prefilters(indicators: dict, spread: float) -> bool:
    """Return True when generic conditions pass."""
    max_spread = float(env_loader.get_env("MAX_SPREAD_PIPS", "2"))
    pip_size = 0.01 if env_loader.get_env("DEFAULT_PAIR", "USD_JPY").endswith("_JPY") else 0.0001
    if spread / pip_size > max_spread:
        return False
    return True


def trend_filters(indicators: dict) -> bool:
    """Return True if trend-specific filters pass."""
    try:
        ema_fast = indicators.get("ema_fast")
        ema_slow = indicators.get("ema_slow")
        if ema_fast is None or ema_slow is None:
            return False
        f = float(ema_fast.iloc[-1]) if hasattr(ema_fast, "iloc") else float(ema_fast[-1])
        s = float(ema_slow.iloc[-1]) if hasattr(ema_slow, "iloc") else float(ema_slow[-1])
        pip_size = 0.01 if env_loader.get_env("DEFAULT_PAIR", "USD_JPY").endswith("_JPY") else 0.0001
        diff = abs(f - s) / pip_size
        min_diff = float(env_loader.get_env("TREND_EMA_DIFF_MIN", "1"))
        return diff >= min_diff
    except Exception:
        return False


__all__ = ["generic_prefilters", "trend_filters"]

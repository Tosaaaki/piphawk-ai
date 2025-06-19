from __future__ import annotations

"""Prefilter utilities for the technical pipeline."""

from datetime import datetime

from backend.filters import session_ok, spread_ok, volatility_ok
from backend.utils import env_loader


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


def _pip_size() -> float:
    return 0.01 if env_loader.get_env("DEFAULT_PAIR", "USD_JPY").endswith("_JPY") else 0.0001


def generic_prefilters(indicators: dict, spread: float) -> bool:
    """Return True when basic session/volatility/spread checks pass."""

    atr = _last(indicators.get("atr"))
    pip_size = _pip_size()
    ctx = {
        "atr": atr,
        "spread": spread / pip_size if spread is not None else None,
        "hour": datetime.utcnow().hour,
    }
    return volatility_ok(ctx) and spread_ok(ctx) and session_ok(ctx)


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

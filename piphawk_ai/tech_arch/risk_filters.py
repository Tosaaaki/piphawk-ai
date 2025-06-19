from __future__ import annotations

"""Basic risk filters for the technical pipeline."""

import logging
import time

from backend.utils import env_loader

logger = logging.getLogger(__name__)

_last_entry_ts: float = 0.0


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


def spread_filter(indicators: dict, spread: float) -> bool:
    atr = _last(indicators.get("atr"))
    if atr is None:
        return True
    limit = float(env_loader.get_env("MAX_SPREAD_ATR_RATIO", "0.15"))
    return spread <= atr * limit


def margin_filter(account: dict | None) -> bool:
    if not account:
        return True
    try:
        nav = float(account.get("NAV") or account.get("balance") or 0.0)
        avail = float(account.get("marginAvailable", 0.0))
        if nav <= 0:
            return True
        return (avail / nav) > 0.05
    except Exception:
        return True


def duplicate_guard() -> bool:
    global _last_entry_ts
    interval = float(env_loader.get_env("DUPLICATE_INTERVAL_SEC", "60"))
    now = time.time()
    if now - _last_entry_ts < interval:
        logger.debug("duplicate_guard blocked entry")
        return False
    _last_entry_ts = now
    return True


def vol_spike_guard(indicators: dict) -> bool:
    atr_series = indicators.get("atr")
    if atr_series is None:
        return True
    try:
        if hasattr(atr_series, "iloc") and len(atr_series) >= 2:
            prev = float(atr_series.iloc[-2])
            last = float(atr_series.iloc[-1])
        elif isinstance(atr_series, (list, tuple)) and len(atr_series) >= 2:
            prev = float(atr_series[-2])
            last = float(atr_series[-1])
        else:
            return True
        if prev <= 0:
            return True
        ratio = last / prev
        threshold = float(env_loader.get_env("VOL_SPIKE_RATIO", "2.0"))
        return ratio < threshold
    except Exception:
        return True


def check_risk(ctx, indicators: dict) -> bool:
    """Evaluate core risk filters and return ``True`` when all pass."""

    return (
        margin_filter(getattr(ctx, "account", None))
        and spread_filter(indicators, getattr(ctx, "spread", 0.0))
        and vol_spike_guard(indicators)
    )


__all__ = ["check_risk", "spread_filter", "margin_filter", "duplicate_guard", "vol_spike_guard"]

from __future__ import annotations

"""M5 signal detection helpers."""

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


def detect_entry(mode: str, candles: list[dict], indicators: dict) -> dict | None:
    """Return signal dict ``{"side": "long"|"short"}`` or ``None``."""
    if len(candles) < 2:
        return None
    last = candles[-1].get("mid", candles[-1])
    prev = candles[-2].get("mid", candles[-2])
    close = float(last.get("c"))
    prev_high = float(prev.get("h"))
    prev_low = float(prev.get("l"))

    if mode == "trend":
        if close > prev_high:
            return {"side": "long"}
        if close < prev_low:
            return {"side": "short"}
        return None

    bb_upper = _last(indicators.get("bb_upper"))
    bb_lower = _last(indicators.get("bb_lower"))
    prev_close = float(prev.get("c"))
    open_p = float(last.get("o", prev_close))

    if bb_lower is not None and prev_close < bb_lower and close > open_p > prev_close:
        return {"side": "long"}
    if bb_upper is not None and prev_close > bb_upper and close < open_p < prev_close:
        return {"side": "short"}

    return None


__all__ = ["detect_entry"]

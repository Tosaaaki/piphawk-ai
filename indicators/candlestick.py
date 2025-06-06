from __future__ import annotations

from typing import Sequence


def upper_shadow_ratio(candle: dict) -> float:
    """Return the upper shadow ratio of a candle."""
    base = candle.get("mid", candle)
    try:
        h = float(base.get("h"))
        l = float(base.get("l"))
        o = float(base.get("o"))
        c = float(base.get("c"))
    except Exception:
        return 0.0
    body_high = max(o, c)
    rng = h - l
    if rng <= 0:
        return 0.0
    return (h - body_high) / rng


def detect_upper_wick_cluster(
    candles: Sequence[dict], ratio: float = 0.6, count: int = 3
) -> bool:
    """Return True if ``count`` recent candles all have long upper shadows."""
    if len(candles) < count:
        return False
    recent = candles[-count:]
    return all(upper_shadow_ratio(c) >= ratio for c in recent)


__all__ = ["upper_shadow_ratio", "detect_upper_wick_cluster"]

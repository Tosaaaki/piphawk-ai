"""M5シグナル検出ロジック."""
from __future__ import annotations

from signals.signal_manager import is_engulfing


def detect_entry(mode: str, candles: list[dict], indicators: dict) -> dict | None:
    """モード別にエントリーシグナルを判定."""
    if len(candles) < 2:
        return None
    prev = candles[-2]
    cur = candles[-1]

    if mode == "trend":
        high_break = float(cur.get("h")) > float(prev.get("h"))
        low_break = float(cur.get("l")) < float(prev.get("l"))
        if high_break:
            return {"side": "long"}
        if low_break:
            return {"side": "short"}
        return None

    # range mode
    upper = indicators.get("bb_upper")
    lower = indicators.get("bb_lower")
    if upper is None or lower is None or not len(upper) or not len(lower):
        return None
    up = float(upper.iloc[-1]) if hasattr(upper, "iloc") else float(upper[-1])
    lo = float(lower.iloc[-1]) if hasattr(lower, "iloc") else float(lower[-1])
    if float(prev.get("h")) >= up and is_engulfing(prev, cur):
        return {"side": "short"}
    if float(prev.get("l")) <= lo and is_engulfing(prev, cur):
        return {"side": "long"}
    return None


__all__ = ["detect_entry"]

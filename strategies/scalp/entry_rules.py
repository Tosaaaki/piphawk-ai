"""Scalp entry rules."""
from __future__ import annotations

from typing import Any, Dict, Optional


def rule_scalp_long(ctx: Dict[str, Any]) -> Optional[str]:
    """スプレッドが閾値以下で下限付近なら買い."""
    spread = ctx.get("spread", 0.0)
    mid = ctx.get("mid")
    lower = ctx.get("lower_band")
    if mid is not None and lower is not None and spread < ctx.get("spread_thresh", 0.02):
        if mid <= lower * 1.001:
            return "long"
    return None


def rule_scalp_short(ctx: Dict[str, Any]) -> Optional[str]:
    """スプレッドが小さく上限付近なら売り."""
    spread = ctx.get("spread", 0.0)
    mid = ctx.get("mid")
    upper = ctx.get("upper_band")
    if mid is not None and upper is not None and spread < ctx.get("spread_thresh", 0.02):
        if mid >= upper * 0.999:
            return "short"
    return None


def rule_breakout(ctx: Dict[str, Any]) -> Optional[str]:
    """直近レンジをブレイクした方向にエントリー."""
    last = ctx.get("price")
    high = ctx.get("range_high")
    low = ctx.get("range_low")
    if last is None or high is None or low is None:
        return None
    if last > high:
        return "long"
    if last < low:
        return "short"
    return None


__all__ = ["rule_scalp_long", "rule_scalp_short", "rule_breakout"]

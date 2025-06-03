"""シグナル管理モジュール."""
from __future__ import annotations

from typing import Sequence


def _body_wick(candle: dict) -> tuple[float, float, float]:
    """ローソク足の実体と上下ヒゲ長を計算."""
    o = float(candle.get("o"))
    h = float(candle.get("h"))
    l = float(candle.get("l"))
    c = float(candle.get("c"))
    body = abs(c - o)
    upper = h - max(c, o)
    lower = min(c, o) - l
    return body, upper, lower


def has_long_wick(candle: dict, ratio: float = 2.0) -> bool:
    """ヒゲが実体の ratio 倍以上なら True."""
    body, upper, lower = _body_wick(candle)
    return upper >= body * ratio or lower >= body * ratio


def is_engulfing(prev: dict, cur: dict) -> bool:
    """包み足判定."""
    prev_o = float(prev.get("o"))
    prev_c = float(prev.get("c"))
    cur_o = float(cur.get("o"))
    cur_c = float(cur.get("c"))
    return (cur_o <= prev_c and cur_c >= prev_o) or (cur_o >= prev_c and cur_c <= prev_o)


def mark_liquidity_sweep(candles: Sequence[dict]) -> bool:
    """直近2本で流動性掃除とみなせば True."""
    if len(candles) < 2:
        return False
    prev, cur = candles[-2], candles[-1]
    if has_long_wick(cur, ratio=2.0) and is_engulfing(prev, cur):
        return True
    return False

__all__ = ["has_long_wick", "is_engulfing", "mark_liquidity_sweep"]

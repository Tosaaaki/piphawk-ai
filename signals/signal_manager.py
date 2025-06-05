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

def compute_trade_score(
    vwap_dev: float,
    atr_boost: float,
    engulfing: bool,
    confluence: bool,
    *,
    reversal_threshold: float = 1.0,
    breakout_threshold: float = 1.5,
    weights: dict[str, float] | None = None,
) -> str | None:
    """複数シグナルを統合してモードを判定する."""

    if weights is None:
        weights = {
            "vwap": 0.4,
            "atr": 0.3,
            "engulfing": 0.2,
            "confluence": 0.1,
        }

    score = (
        vwap_dev * weights.get("vwap", 0)
        + atr_boost * weights.get("atr", 0)
        + (1.0 if engulfing else 0.0) * weights.get("engulfing", 0)
        + (1.0 if confluence else 0.0) * weights.get("confluence", 0)
    )

    if score >= breakout_threshold:
        return "breakout"
    if score >= reversal_threshold:
        return "range_reversal"
    return None


__all__ = ["has_long_wick", "is_engulfing", "mark_liquidity_sweep", "compute_trade_score"]

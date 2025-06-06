from __future__ import annotations

"""Simple multi timeframe scalp utilities."""

from typing import Sequence, Optional

from indicators.bollinger import multi_bollinger


def analyze_environment_m1(closes: Sequence[float]) -> str:
    """Return ``"trend"`` or ``"range"`` based on Bollinger band width."""
    data = {"M1": closes}
    bands = multi_bollinger(data)["M1"]
    width = bands["upper"] - bands["lower"]
    if len(closes) < 2:
        return "range"
    prev = multi_bollinger({"M1": closes[:-1]})["M1"]
    prev_width = prev["upper"] - prev["lower"]
    return "trend" if width > prev_width else "range"


def should_enter_trade_s10(
    direction: str,
    closes: Sequence[float],
    bands_s10: dict,
) -> Optional[str]:
    """Return order side ``"long"`` or ``"short"`` if conditions met."""
    if not closes:
        return None
    price = closes[-1]
    upper = bands_s10["upper"]
    lower = bands_s10["lower"]
    if direction == "trend":
        if price > upper:
            return "long"
        if price < lower:
            return "short"
    else:
        if len(closes) < 2:
            return None
        prev = closes[-2]
        if prev < lower and price > lower:
            return "long"
        if prev > upper and price < upper:
            return "short"
    return None


__all__ = ["analyze_environment_m1", "should_enter_trade_s10"]


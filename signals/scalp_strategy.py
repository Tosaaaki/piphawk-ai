from __future__ import annotations

"""Simple multi timeframe scalp utilities."""

from typing import Sequence, Optional

from indicators.bollinger import multi_bollinger
from indicators.patterns import DoubleBottomSignal, DoubleTopSignal
from backend.utils import env_loader


SCALP_COND_TF = env_loader.get_env("SCALP_COND_TF", "M1").upper()


def analyze_environment_tf(closes: Sequence[float], tf: str | None = None) -> str:
    """Return ``"trend"`` or ``"range"`` based on Bollinger band width."""
    tf = (tf or env_loader.get_env("SCALP_COND_TF", SCALP_COND_TF)).upper()
    data = {tf: closes}
    bands = multi_bollinger(data)[tf]
    width = bands["upper"] - bands["lower"]
    if len(closes) < 2:
        return "range"
    prev = multi_bollinger({tf: closes[:-1]})[tf]
    prev_width = prev["upper"] - prev["lower"]
    return "trend" if width > prev_width else "range"


def analyze_environment_m1(closes: Sequence[float]) -> str:
    """Compatibility wrapper using the M1 timeframe."""
    return analyze_environment_tf(closes, "M1")


def should_enter_trade_s10(
    direction: str,
    closes: Sequence[float],
    bands_s10: dict,
    candles: Sequence[dict] | None = None,
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
            if candles:
                subset = candles[-4:] if len(candles) >= 4 else candles
                pattern = DoubleBottomSignal().evaluate(subset)
                if pattern is None:
                    return None
            return "long"
        if prev > upper and price < upper:
            if candles:
                subset = candles[-4:] if len(candles) >= 4 else candles
                pattern = DoubleTopSignal().evaluate(subset)
                if pattern is None:
                    return None
            return "short"
    return None


__all__ = ["analyze_environment_tf", "analyze_environment_m1", "should_enter_trade_s10"]


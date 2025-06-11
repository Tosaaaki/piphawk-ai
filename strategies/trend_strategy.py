"""Simple trend-follow strategy wrapper."""

from __future__ import annotations

from typing import Any, Dict

from strategies.base import Strategy


class TrendStrategy(Strategy):
    """単純なトレンドフォロー戦略."""

    LOOKBACK = 5

    def __init__(self) -> None:
        super().__init__("trend")

    def decide_entry(self, context: Dict[str, Any]) -> str | None:
        closes = context.get("closes", [])
        if len(closes) < 2:
            return None

        ema = (
            context.get("ema50_h1")
            or context.get("ema_fast_h1")
            or context.get("ema_h1")
        )
        ema_slope = context.get("ema_slope_h1")
        highs = context.get("highs")
        lows = context.get("lows")

        if (
            ema is not None
            and ema_slope is not None
            and highs is not None
            and lows is not None
            and len(highs) >= self.LOOKBACK
            and len(lows) >= self.LOOKBACK
        ):
            price = closes[-1]
            prev_price = closes[-2]
            recent_high = max(highs[-self.LOOKBACK :])
            recent_low = min(lows[-self.LOOKBACK :])

            if price > ema and ema_slope > 0:
                if price > recent_high and prev_price <= recent_high:
                    return "long"
            if price < ema and ema_slope < 0:
                if price < recent_low and prev_price >= recent_low:
                    return "short"

        last = closes[-1]
        prev = closes[-2]
        if last > prev:
            return "long"
        if last < prev:
            return "short"
        return None

    def execute_trade(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        side = self.decide_entry(context)
        if side is None:
            return None
        return {"strategy": self.name, "side": side}


class StrongTrendStrategy(TrendStrategy):
    """強トレンド時の即時エントリー戦略."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "strong_trend"



__all__ = ["TrendStrategy", "StrongTrendStrategy"]

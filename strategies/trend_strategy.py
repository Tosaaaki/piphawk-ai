"""Simple trend-follow strategy wrapper."""

from __future__ import annotations

from typing import Any, Dict

from strategies.base import Strategy


class TrendStrategy(Strategy):
    """単純なトレンドフォロー戦略."""

    def __init__(self) -> None:
        super().__init__("trend")

    def decide_entry(self, context: Dict[str, Any]) -> str | None:
        closes = context.get("closes", [])
        if len(closes) < 2:
            return None
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


__all__ = ["TrendStrategy"]

"""Simple scalp strategy wrapper."""

from __future__ import annotations

from typing import Any, Dict

from strategies.base import Strategy
from signals.scalp_strategy import (
    analyze_environment_tf,
    should_enter_trade_s10,
)
from indicators.bollinger import multi_bollinger


class ScalpStrategy(Strategy):
    """ボリンジャーバンドを用いたスキャルピング戦略."""

    def __init__(self) -> None:
        super().__init__("scalp")

    def decide_entry(self, context: Dict[str, Any]) -> str | None:
        closes = context.get("closes", [])
        if not closes:
            return None
        bands = multi_bollinger({"S10": closes})["S10"]
        env = analyze_environment_tf(closes, "S10")
        return should_enter_trade_s10(env, closes, bands)

    def execute_trade(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        side = self.decide_entry(context)
        if side is None:
            return None
        return {"strategy": self.name, "side": side}


__all__ = ["ScalpStrategy"]

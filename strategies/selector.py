"""Strategy selection via contextual bandit."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from mabwiser.mab import MAB, LearningPolicy

from strategies.base import Strategy
from backend.scheduler.policy_updater import OfflinePolicy


class StrategySelector:
    """Contextual bandit で戦略を選択するクラス."""

    def __init__(self, strategies: Dict[str, Strategy], alpha: float = 1.0, use_offline_policy: bool = False) -> None:
        self.strategies = strategies
        arms = list(strategies.keys())
        self.bandit = MAB(arms=arms, learning_policy=LearningPolicy.LinUCB(alpha=alpha))
        self.bandit.fit([], [], np.empty((0,1)))
        self.offline_policy = OfflinePolicy() if use_offline_policy else None

    def _vec(self, context: Dict[str, Any]) -> List[float]:
        """辞書コンテキストを数値ベクトルへ変換."""
        return [float(context.get(k, 0.0)) for k in sorted(context.keys())]

    def select(self, context: Dict[str, Any]) -> Strategy:
        if self.offline_policy is not None:
            name = self.offline_policy.select(context)
            if name and name in self.strategies:
                return self.strategies[name]
        ctx = [self._vec(context)]
        arm = self.bandit.predict(ctx)
        return self.strategies[arm]

    def update(self, arm: str, context: Dict[str, Any], reward: float) -> None:
        ctx = [self._vec(context)]
        self.bandit.partial_fit([arm], [reward], ctx)

    def available_strategies(self) -> List[str]:
        return list(self.strategies.keys())


__all__ = ["StrategySelector"]

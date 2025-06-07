"""Entry rule selector with LinUCB."""
from __future__ import annotations

from typing import Any, Callable, Dict

import numpy as np
from mabwiser.mab import MAB, LearningPolicy


class RuleSelector:
    """複数ルールから最適なものを選択するセレクタ."""

    def __init__(self, rules: Dict[str, Callable[[Dict[str, Any]], str | None]], alpha: float = 1.0) -> None:
        self.rules = rules
        arms = list(rules.keys())
        self.bandit = MAB(arms=arms, learning_policy=LearningPolicy.LinUCB(alpha=alpha))
        self.bandit.fit([], [], np.empty((0, 1)))

    def _vec(self, ctx: Dict[str, Any]) -> list[float]:
        return [float(ctx.get(k, 0.0)) for k in sorted(ctx.keys())]

    def choose_rule(self, ctx: Dict[str, Any]) -> str:
        arm = self.bandit.predict([self._vec(ctx)])
        return arm

    def evaluate(self, ctx: Dict[str, Any]) -> str | None:
        arm = self.choose_rule(ctx)
        return self.rules[arm](ctx)

    def update_reward(self, arm: str, ctx: Dict[str, Any], reward: float) -> None:
        self.bandit.partial_fit([arm], [reward], [self._vec(ctx)])

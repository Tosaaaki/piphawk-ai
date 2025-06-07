"""Bandit based strategy manager."""

from __future__ import annotations

from typing import List

from mabwiser.mab import MAB, LearningPolicy


class BanditStrategyManager:
    """UCB1 アルゴリズムで戦略を選択するマネージャ."""

    def __init__(self, arms: List[str], alpha: float = 1.3) -> None:
        self.mab = MAB(arms, LearningPolicy.UCB1(alpha=alpha))
        self.mab.fit(decisions=[], rewards=[])

    def select_arm(self) -> str:
        return self.mab.predict()[0]

    def update_reward(self, arm: str, reward: float) -> None:
        self.mab.partial_fit(decisions=[arm], rewards=[reward])


__all__ = ["BanditStrategyManager"]

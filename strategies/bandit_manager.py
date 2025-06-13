"""Bandit based strategy manager."""

from __future__ import annotations

from typing import Any, List

try:
    from mabwiser.mab import MAB, LearningPolicy
except Exception:  # pragma: no cover - fallback when dependency fails
    class _FallbackMAB:
        def __init__(self, arms, learning_policy=None):
            self.arms = list(arms)
            self.index = 0

        def fit(self, *args, **kwargs):
            pass

        def predict(self, *_: Any):
            arm = self.arms[self.index % len(self.arms)]
            self.index += 1
            return [arm]

        def partial_fit(self, *args, **kwargs):
            pass

    class _FallbackPolicy:
        class UCB1:
            def __init__(self, alpha: float = 1.0) -> None:
                self.alpha = alpha

    MAB = _FallbackMAB
    LearningPolicy = _FallbackPolicy


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

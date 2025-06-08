from __future__ import annotations

"""Strategy selection using LinUCB with optional offline policy."""

import logging
from typing import Any, Dict, List

import numpy as np
from mabwiser.mab import MAB, LearningPolicy

from backend.utils import env_loader
from strategies.base import Strategy
from piphawk_ai.policy.offline import OfflinePolicy

logger = logging.getLogger(__name__)


class StrategySelector:
    """Contextual bandit strategy selector."""

    def __init__(
        self,
        strategies: Dict[str, Strategy],
        alpha: float = 1.0,
        use_offline_policy: bool | None = None,
    ) -> None:
        self.strategies = strategies
        arms = list(strategies.keys())
        try:
            self.bandit = MAB(arms=arms, learning_policy=LearningPolicy.LinUCB(alpha=alpha))
            self.bandit.fit([], [], np.empty((0, 1)))
        except Exception as exc:  # pragma: no cover - fallback on import issues
            logger.warning("LinUCB init failed: %s", exc)
            self.bandit = None
        if use_offline_policy is None:
            use_offline_policy = env_loader.get_env("USE_OFFLINE_POLICY", "false").lower() == "true"
        if use_offline_policy:
            try:
                path = env_loader.get_env("POLICY_PATH", "policies/latest_policy.pkl")
                self.offline_policy = OfflinePolicy(path)
            except Exception as exc:  # pragma: no cover - load failure
                logger.warning("OfflinePolicy init failed: %s", exc)
                self.offline_policy = None
        else:
            self.offline_policy = None

    def _vec(self, context: Dict[str, Any]) -> List[float]:
        """Convert context dict to numeric vector."""
        return [float(context.get(k, 0.0)) for k in sorted(context.keys())]

    def select(self, context: Dict[str, Any]) -> Strategy:
        if self.offline_policy is not None:
            try:
                name = self.offline_policy.select(context)
            except Exception as exc:  # pragma: no cover - model failure
                logger.warning("OfflinePolicy selection failed: %s", exc)
                name = None
            if name and name in self.strategies:
                logger.info("OfflinePolicy selected: %s", name)
                return self.strategies[name]
        ctx = [self._vec(context)]
        if self.bandit is not None:
            try:
                arm = self.bandit.predict(ctx)
                return self.strategies[arm]
            except Exception as exc:  # pragma: no cover
                logger.warning("Bandit prediction failed: %s", exc)
        # Fallback to first strategy
        return next(iter(self.strategies.values()))

    def update(self, arm: str, context: Dict[str, Any], reward: float) -> None:
        if self.bandit is None:
            return
        ctx = [self._vec(context)]
        self.bandit.partial_fit([arm], [reward], ctx)

    def available_strategies(self) -> List[str]:
        return list(self.strategies.keys())


__all__ = ["StrategySelector"]

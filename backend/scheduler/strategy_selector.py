from __future__ import annotations

"""Strategy selection using LinUCB with optional offline policy."""

import logging
import sys
import types
from typing import Any, Dict, List

import numpy as np
try:  # pandas may be stubbed during testing
    import pandas as _pd  # type: ignore
    if not hasattr(_pd, "DataFrame"):
        raise ImportError
except Exception:  # pragma: no cover - minimal stub for mabwiser
    _pd = types.SimpleNamespace(DataFrame=list, Series=list)
    sys.modules["pandas"] = _pd
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
        self.alpha = alpha
        bandit_enabled = env_loader.get_env("BANDIT_ENABLED", "true").lower() == "true"
        if bandit_enabled:
            try:
                self.bandit = MAB(arms=arms, learning_policy=LearningPolicy.LinUCB(alpha=alpha))
            except Exception as exc:  # pragma: no cover - fallback on import issues
                logger.warning("LinUCB init failed: %s", exc)
                self.bandit = None
        else:
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

    def _ensure_bandit_ready(self, ctx: List[List[float]]) -> None:
        """Fit or reinitialize bandit when context dimension changes."""
        if self.bandit is None:
            return
        dim = len(ctx[0])
        try:
            if not getattr(self.bandit, "_is_initial_fit", False):
                self.bandit.fit([], [], np.empty((0, dim)))
            elif getattr(self.bandit._imp, "num_features", None) != dim:
                self.bandit = MAB(
                    arms=list(self.strategies.keys()),
                    learning_policy=LearningPolicy.LinUCB(alpha=self.alpha),
                )
                self.bandit.fit([], [], np.empty((0, dim)))
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.warning("LinUCB init failed: %s", exc)
            self.bandit = None

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
                self._ensure_bandit_ready(ctx)
                if self.bandit is not None:
                    arm = self.bandit.predict(ctx)
                    return self.strategies[arm]
            except Exception as exc:  # pragma: no cover
                dim = len(ctx[0])
                num_features = getattr(getattr(self.bandit, "_imp", None), "num_features", None)
                logger.warning(
                    "Bandit prediction failed: %s dim=%s num_features=%s",
                    exc,
                    dim,
                    num_features,
                )
                try:
                    self._ensure_bandit_ready(ctx)
                    if self.bandit is not None:
                        arm = self.bandit.predict(ctx)
                        return self.strategies[arm]
                except Exception as exc2:  # pragma: no cover
                    logger.warning("Bandit prediction failed after retry: %s", exc2)
        # Fallback to first strategy
        return next(iter(self.strategies.values()))

    def update(self, arm: str, context: Dict[str, Any], reward: float) -> None:
        if self.bandit is None:
            return
        ctx = [self._vec(context)]
        try:
            self._ensure_bandit_ready(ctx)
            if self.bandit is not None:
                self.bandit.partial_fit([arm], [reward], ctx)
        except Exception as exc:  # pragma: no cover
            logger.warning("Bandit update failed: %s", exc)

    def available_strategies(self) -> List[str]:
        return list(self.strategies.keys())


__all__ = ["StrategySelector"]

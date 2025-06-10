"""Entry rule selector with LinUCB."""
from __future__ import annotations

from typing import Any, Callable, Dict

import numpy as np
from mabwiser.mab import MAB, LearningPolicy


class RuleSelector:
    """複数ルールから最適なものを選択するセレクタ."""

    def __init__(self, rules: Dict[str, Callable[[Dict[str, Any]], str | None]], alpha: float = 1.0) -> None:
        self.rules = rules
        self.alpha = alpha
        arms = list(rules.keys())
        self.bandit = MAB(arms=arms, learning_policy=LearningPolicy.LinUCB(alpha=alpha))
        self.bandit.fit([], [], np.empty((0, 1)))

    def _ensure_bandit_ready(self, ctx: list[list[float]]) -> None:
        """コンテキスト次元に合わせてバンディットを初期化する."""
        dim = len(ctx[0])
        if not getattr(self.bandit, "_is_initial_fit", False):
            self.bandit.fit([], [], np.empty((0, dim)))
        elif getattr(self.bandit._imp, "num_features", None) != dim:
            self.bandit = MAB(arms=list(self.rules.keys()), learning_policy=LearningPolicy.LinUCB(alpha=self.alpha))
            self.bandit.fit([], [], np.empty((0, dim)))

    def _vec(self, ctx: Dict[str, Any]) -> list[float]:
        return [float(ctx.get(k, 0.0)) for k in sorted(ctx.keys())]

    def choose_rule(self, ctx: Dict[str, Any]) -> str:
        arr = [self._vec(ctx)]
        self._ensure_bandit_ready(arr)
        arm = self.bandit.predict(arr)
        return arm

    def evaluate(self, ctx: Dict[str, Any]) -> str | None:
        arm = self.choose_rule(ctx)
        return self.rules[arm](ctx)

    def update_reward(self, arm: str, ctx: Dict[str, Any], reward: float) -> None:
        arr = [self._vec(ctx)]
        self._ensure_bandit_ready(arr)
        self.bandit.partial_fit([arm], [reward], arr)


def build_entry_context(data: Dict[str, Any]) -> Dict[str, float]:
    """エントリールール選択用のコンテキストを生成するユーティリティ."""
    ctx: Dict[str, float] = {}
    spread = data.get("spread")
    if spread is not None:
        try:
            ctx["spread"] = float(spread)
        except Exception:
            pass
    mid = data.get("mid")
    upper = data.get("upper_band")
    lower = data.get("lower_band")
    if mid is not None and upper is not None:
        try:
            ctx["dist_upper"] = float(upper) - float(mid)
        except Exception:
            pass
    if mid is not None and lower is not None:
        try:
            ctx["dist_lower"] = float(mid) - float(lower)
        except Exception:
            pass
    price = data.get("price")
    high = data.get("range_high")
    low = data.get("range_low")
    if price is not None and high is not None:
        try:
            ctx["dist_high"] = float(high) - float(price)
        except Exception:
            pass
    if price is not None and low is not None:
        try:
            ctx["dist_low"] = float(price) - float(low)
        except Exception:
            pass
    adx_val = data.get("adx")
    if adx_val is not None:
        try:
            ctx["adx"] = float(adx_val)
        except Exception:
            pass
    return ctx


__all__ = ["RuleSelector", "build_entry_context"]

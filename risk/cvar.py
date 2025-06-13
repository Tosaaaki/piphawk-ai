from __future__ import annotations

"""CVaR (Expected Shortfall) 計算ユーティリティ."""

import math
from typing import Sequence


def calc_cvar(returns: Sequence[float], alpha: float = 0.05) -> float:
    """指定した信頼水準での平均損失を返す。"""
    if not returns:
        raise ValueError("returns must not be empty")
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0,1]")
    sorted_returns = sorted(returns)
    idx = max(1, math.ceil(len(sorted_returns) * alpha))
    tail = sorted_returns[:idx]
    return sum(tail) / len(tail)

__all__ = ["calc_cvar"]

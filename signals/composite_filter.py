from __future__ import annotations

"""Composite scoring filter for trade signals."""

import os
from typing import Any, Callable

from backend.utils import env_loader


def rsi_edge(ctx: dict[str, Any]) -> float:
    """Return ``1.0`` when RSI is outside the neutral band."""
    rsi = ctx.get("rsi")
    try:
        val = float(rsi)
    except Exception:
        return 0.0
    low = float(env_loader.get_env("RSI_EDGE_LOW", "30"))
    high = float(env_loader.get_env("RSI_EDGE_HIGH", "70"))
    return 1.0 if val <= low or val >= high else 0.0


def bb_break(ctx: dict[str, Any]) -> float:
    """Return ``1.0`` when price breaks the Bollinger Band."""
    price = ctx.get("price")
    upper = ctx.get("bb_upper")
    lower = ctx.get("bb_lower")
    try:
        p = float(price)
        u = float(upper)
        l = float(lower)
    except Exception:
        return 0.0
    return 1.0 if p >= u or p <= l else 0.0


def ai_pattern(ctx: dict[str, Any]) -> float:
    """Return pattern score from context."""
    score = ctx.get("ai_pattern")
    try:
        return float(score)
    except Exception:
        return 0.0


def _load_weights() -> dict[str, float]:
    weights: dict[str, float] = {}
    prefix = "COMPOSITE_FILTER_WEIGHTS_"
    for key, val in os.environ.items():
        if not key.startswith(prefix):
            continue
        name = key[len(prefix) :].lower()
        try:
            weights[name] = float(val)
        except ValueError:
            continue
    return weights


class CompositeFilter:
    """Scoring filter aggregating multiple evaluators."""

    def __init__(self, min_score: float | None = None, weights: dict[str, float] | None = None) -> None:
        self.min_score = min_score if min_score is not None else float(
            env_loader.get_env("COMPOSITE_FILTER_MIN_SCORE", "2")
        )
        self.weights = weights if weights is not None else _load_weights()
        self.functions: dict[str, Callable[[dict[str, Any]], float]] = {}

    def register(self, name: str, func: Callable[[dict[str, Any]], float]) -> None:
        """Register evaluation function under ``name``."""
        self.functions[name] = func

    def evaluate(self, ctx: dict[str, Any]) -> float:
        """Return weighted sum of registered scores."""
        score = 0.0
        for name, func in self.functions.items():
            try:
                val = float(func(ctx))
            except Exception:
                val = 0.0
            w = self.weights.get(name, 1.0)
            score += val * w
        return score

    def pass_(self, ctx: dict[str, Any]) -> bool:
        """Return ``True`` when the evaluated score meets ``min_score``."""
        return self.evaluate(ctx) >= self.min_score


DEFAULT_FILTER = CompositeFilter()
DEFAULT_FILTER.register("rsi_edge", rsi_edge)
DEFAULT_FILTER.register("bb_break", bb_break)
# ai_pattern はフィルター後に AI で評価するため除外する

__all__ = [
    "CompositeFilter",
    "rsi_edge",
    "bb_break",
    "DEFAULT_FILTER",
]

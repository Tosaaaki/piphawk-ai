"""Multi timeframe alignment checks."""
from __future__ import annotations

import logging
from typing import Dict, Literal
from backend.utils import env_loader

logger = logging.getLogger(__name__)

Direction = Literal["long", "short"]


def _ema_direction(ema_fast, ema_slow) -> Direction | None:
    """Return direction based on EMA fast/slow relationship."""
    try:
        fast = ema_fast.iloc[-1] if hasattr(ema_fast, "iloc") else ema_fast[-1]
        slow = ema_slow.iloc[-1] if hasattr(ema_slow, "iloc") else ema_slow[-1]
    except Exception:
        return None
    if fast > slow:
        return "long"
    if fast < slow:
        return "short"
    return None


def is_multi_tf_aligned(indicators_by_tf: Dict[str, Dict]) -> Direction | None:
    """Return unified direction when multiple timeframes agree."""
    weights_env = env_loader.get_env("TF_EMA_WEIGHTS", "M5:0.4,H1:0.3,H4:0.3")
    weights: Dict[str, float] = {}
    for part in weights_env.split(","):
        if ":" in part:
            key, val = part.split(":", 1)
            try:
                weights[key.strip().upper()] = float(val)
            except ValueError:
                continue

    scores: Dict[Direction, float] = {"long": 0.0, "short": 0.0}
    for tf, ind in indicators_by_tf.items():
        dir_ = _ema_direction(ind.get("ema_fast"), ind.get("ema_slow"))
        w = weights.get(tf.upper(), 0.0)
        if dir_:
            scores[dir_] += w
        else:
            logger.debug("%s: insufficient EMA data for alignment", tf)

    if scores["long"] > scores["short"] and scores["long"] >= 0.5:
        return "long"
    if scores["short"] > scores["long"] and scores["short"] >= 0.5:
        return "short"
    return None

__all__ = ["is_multi_tf_aligned"]

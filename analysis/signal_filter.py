"""Multi timeframe alignment checks."""
from __future__ import annotations

import logging
from typing import Dict, Literal

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
    votes: Dict[Direction, int] = {"long": 0, "short": 0}
    for tf, ind in indicators_by_tf.items():
        dir_ = _ema_direction(ind.get("ema_fast"), ind.get("ema_slow"))
        if dir_:
            votes[dir_] += 1
        else:
            logger.debug("%s: insufficient EMA data for alignment", tf)
    if votes["long"] > votes["short"] and votes["long"] >= 2:
        return "long"
    if votes["short"] > votes["long"] and votes["short"] >= 2:
        return "short"
    return None

__all__ = ["is_multi_tf_aligned"]

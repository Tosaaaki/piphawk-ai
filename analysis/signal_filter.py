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


def is_multi_tf_aligned(
    indicators_by_tf: Dict[str, Dict], ai_side: Direction | None = None
) -> Direction | None:
    """Return unified direction when multiple timeframes and AI agree."""

    bypass_adx = float(env_loader.get_env("ALIGN_BYPASS_ADX", "0"))
    if ai_side in ("long", "short") and bypass_adx > 0:
        m5 = indicators_by_tf.get("M5") or indicators_by_tf.get("m5")
        adx = m5.get("adx") if m5 else None
        try:
            if adx is not None:
                latest = adx.iloc[-1] if hasattr(adx, "iloc") else adx[-1]
                if float(latest) >= bypass_adx:
                    logger.debug(
                        "Bypassing multi-TF alignment as ADX %.2f >= %.2f",
                        float(latest),
                        bypass_adx,
                    )
                    return ai_side
        except Exception:
            pass

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

    if ai_side in ("long", "short"):
        ai_w = float(env_loader.get_env("AI_ALIGN_WEIGHT", "0.2"))
        scores[ai_side] += ai_w

    long_score = scores["long"]
    short_score = scores["short"]
    if long_score == short_score and ai_side in ("long", "short"):
        return ai_side
    if long_score > short_score:
        return "long" if long_score >= 0.5 or ai_side == "long" else None
    if short_score > long_score:
        return "short" if short_score >= 0.5 or ai_side == "short" else None
    return ai_side if ai_side in ("long", "short") else None

__all__ = ["is_multi_tf_aligned"]

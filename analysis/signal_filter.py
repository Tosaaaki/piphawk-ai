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


def _adx_direction(adx, plus_di, minus_di, min_adx: float) -> Direction | None:
    """Return direction based on ADX DI values when ADX >= min_adx."""
    try:
        adx_val = (
            float(adx.iloc[-1]) if hasattr(adx, "iloc") else float(adx[-1])
        )
        p = plus_di.iloc[-1] if hasattr(plus_di, "iloc") else plus_di[-1]
        m = minus_di.iloc[-1] if hasattr(minus_di, "iloc") else minus_di[-1]
    except Exception:
        return None
    try:
        p = float(p)
        m = float(m)
    except Exception:
        return None
    if adx_val < min_adx:
        return None
    if p > m:
        return "long"
    if p < m:
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

    weights_env = env_loader.get_env(
        "TF_EMA_WEIGHTS", "M5:0.4,M15:0.2,H1:0.3,H4:0.1"
    )
    weights: Dict[str, float] = {}
    for part in weights_env.split(","):
        if ":" in part:
            key, val = part.split(":", 1)
            try:
                weights[key.strip().upper()] = float(val)
            except ValueError:
                continue

    adx_weight = float(env_loader.get_env("ALIGN_ADX_WEIGHT", "0"))
    min_adx = float(env_loader.get_env("MIN_ALIGN_ADX", "20"))

    lt_adx_thresh = float(env_loader.get_env("LT_TF_PRIORITY_ADX", "0"))
    lt_weight_factor = float(env_loader.get_env("LT_TF_WEIGHT_FACTOR", "1"))
    if lt_adx_thresh > 0 and lt_weight_factor < 1:
        lt_key = "M1" if any(k.lower() == "m1" for k in indicators_by_tf.keys()) else "M5"
        lt_ind = indicators_by_tf.get(lt_key) or indicators_by_tf.get(lt_key.lower())
        if lt_ind:
            adx = lt_ind.get("adx")
            ema_fast = lt_ind.get("ema_fast")
            ema_slow = lt_ind.get("ema_slow")
            try:
                adx_latest = (
                    float(adx.iloc[-1]) if hasattr(adx, "iloc") else float(adx[-1])
                )
                prev_fast = (
                    ema_fast.iloc[-2] if hasattr(ema_fast, "iloc") else ema_fast[-2]
                )
                latest_fast = (
                    ema_fast.iloc[-1] if hasattr(ema_fast, "iloc") else ema_fast[-1]
                )
                prev_slow = (
                    ema_slow.iloc[-2] if hasattr(ema_slow, "iloc") else ema_slow[-2]
                )
                latest_slow = (
                    ema_slow.iloc[-1] if hasattr(ema_slow, "iloc") else ema_slow[-1]
                )
                cross = (
                    (prev_fast < prev_slow and latest_fast > latest_slow)
                    or (prev_fast > prev_slow and latest_fast < latest_slow)
                )
                if adx_latest >= lt_adx_thresh and cross:
                    logger.debug(
                        "Lower TF dominance: ADX %.2f >= %.2f with EMA cross",
                        adx_latest,
                        lt_adx_thresh,
                    )
                    for k in list(weights.keys()):
                        if k != lt_key:
                            weights[k] *= lt_weight_factor
            except Exception:
                pass

    scores: Dict[Direction, float] = {"long": 0.0, "short": 0.0}
    for tf, ind in indicators_by_tf.items():
        dir_ = _ema_direction(ind.get("ema_fast"), ind.get("ema_slow"))
        w = weights.get(tf.upper(), 0.0)
        if dir_:
            scores[dir_] += w
        else:
            logger.debug("%s: insufficient EMA data for alignment", tf)

        if adx_weight > 0:
            adx_dir = _adx_direction(
                ind.get("adx"),
                ind.get("plus_di"),
                ind.get("minus_di"),
                min_adx,
            )
            if adx_dir:
                scores[adx_dir] += w * adx_weight

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

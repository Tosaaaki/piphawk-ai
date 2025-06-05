"""Helper functions for validating AI trade plans."""

from __future__ import annotations

from backend.config.defaults import MIN_ABS_SL_PIPS


def normalize_probs(tp_prob: float, sl_prob: float) -> tuple[float, float]:
    """Return probabilities normalized to sum to 1 when total within [0.5, 1.5]."""
    try:
        tp = float(tp_prob)
        sl = float(sl_prob)
        total = tp + sl
        if 0.5 <= total <= 1.5 and total > 0:
            tp /= total
            sl /= total
        return tp, sl
    except Exception:
        return tp_prob, sl_prob


def risk_autofix(risk: dict | None) -> dict:
    """Ensure risk dictionary contains tp_pips/sl_pips/tp_prob/sl_prob values."""
    if risk is None:
        risk = {}
    try:
        tp = float(risk.get("tp_pips", 10))
    except Exception:
        tp = 8.0
    try:
        sl = float(risk.get("sl_pips", 6))
    except Exception:
        sl = 4.0
    sl = max(sl, MIN_ABS_SL_PIPS)
    try:
        tp_prob = float(risk.get("tp_prob", 0.6))
    except Exception:
        tp_prob = 0.6
    try:
        sl_prob = float(risk.get("sl_prob", 0.4))
    except Exception:
        sl_prob = 0.4
    tp_prob, sl_prob = normalize_probs(tp_prob, sl_prob)
    return {"tp_pips": tp, "sl_pips": sl, "tp_prob": tp_prob, "sl_prob": sl_prob}

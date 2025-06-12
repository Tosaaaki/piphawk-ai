"""Final safety checks for entry plans."""
from __future__ import annotations

from backend.utils import env_loader
from .ai_entry_plan import EntryPlan

EMA_DIFF_THRESHOLD = float(env_loader.get_env("EMA_DIFF_THRESHOLD", "0.0"))
MIN_RRR = float(env_loader.get_env("MIN_RRR", "0.8"))
MIN_NET_TP_PIPS = float(env_loader.get_env("MIN_NET_TP_PIPS", "1"))


def ema_divergence_ok(diff: float) -> bool:
    return diff >= EMA_DIFF_THRESHOLD


def rrr_ok(tp: float, sl: float) -> bool:
    if sl == 0:
        return False
    return (tp / sl) >= MIN_RRR


def net_tp_ok(tp: float, spread: float) -> bool:
    return (tp - spread) >= MIN_NET_TP_PIPS


def final_filter(plan: EntryPlan, indicators: dict) -> bool:
    """Return True if plan passes all filters."""
    diff = float(indicators.get("ema_diff", 0))
    spread = float(indicators.get("spread", 0))
    return all(
        [
            ema_divergence_ok(diff),
            rrr_ok(plan.tp, plan.sl),
            net_tp_ok(plan.tp, spread),
        ]
    )

__all__ = ["final_filter"]

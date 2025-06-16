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
    """Post-filter を全て無効化して必ず True を返す."""
    return True

__all__ = ["final_filter"]

from __future__ import annotations

"""Simple rule validator for entry plans."""

from backend.utils import env_loader


def validate_plan(plan: dict) -> bool:
    """Return True if the plan satisfies minimum RRR."""
    try:
        tp = float(plan.get("tp", 0))
        sl = float(plan.get("sl", 0))
        if sl <= 0:
            return False
        min_rrr = float(env_loader.get_env("MIN_RRR", "1.0"))
        return (tp / sl) >= min_rrr
    except Exception:
        return False


__all__ = ["validate_plan"]

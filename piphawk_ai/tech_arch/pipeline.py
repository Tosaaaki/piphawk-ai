from __future__ import annotations

"""Technical entry pipeline orchestration."""

from backend.orders import get_order_manager
from backend.utils import env_loader
from monitoring import metrics_publisher

from .market_context import build as build_context
from .indicator_engine import compute
from .mode_detector import detect_mode
from .prefilters import generic_prefilters, trend_filters
from .entry_gate import ask_entry
from .rule_validator import validate_plan
from .post_filters import apply_post_filters


def run_cycle() -> dict | None:
    """Run one iteration of the technical entry pipeline."""
    ctx = build_context()
    indicators = compute(ctx.candles)
    mode = detect_mode(indicators, ctx.candles)

    if not generic_prefilters(indicators, ctx.spread):
        return None
    if mode.startswith("trend") and not trend_filters(indicators):
        return None

    plan = ask_entry(mode, indicators)
    if not plan:
        return None
    if not validate_plan(plan):
        return None
    if not apply_post_filters(ctx.candles, indicators):
        return None

    manager = get_order_manager()
    instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    side = plan.get("side", "long")
    tp = float(plan.get("tp", 0))
    sl = float(plan.get("sl", 0))
    lot = int(plan.get("lot", 1))
    manager.place_market_with_tp_sl(instrument, lot, side, tp, sl)

    try:
        metrics_publisher.incr_metric("tech_entry_total", 1, {"mode": mode})
    except Exception:
        pass
    return plan


__all__ = ["run_cycle"]

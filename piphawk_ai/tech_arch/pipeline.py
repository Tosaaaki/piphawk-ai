from __future__ import annotations

"""M5 technical entry pipeline orchestrator."""

import logging

from backend.orders import get_order_manager
from backend.utils import env_loader
from monitoring import metrics_publisher

from .ai_decision import call_llm
from .indicator_engine import compute
from .m5_entry import detect_entry
from .market_classifier import classify_market
from .market_context import build as build_context
from .prefilters import generic_prefilters
from .risk_filters import check_risk

ENTRY_USE_AI = env_loader.get_env("ENTRY_USE_AI", "true").lower() == "true"


def run_cycle() -> dict | None:
    """Run one iteration of the simplified M5 pipeline."""
    ctx = build_context()
    indicators = compute(ctx.candles)

    if not check_risk(ctx, indicators):
        return None

    if not generic_prefilters(indicators, ctx.spread):
        return None

    mode = classify_market(indicators)

    signal = detect_entry(mode, ctx.candles, indicators)
    if not signal:
        return None

    if ENTRY_USE_AI:
        try:
            decision = call_llm(mode, signal, indicators)
        except Exception as exc:  # pragma: no cover - unexpected errors
            logging.getLogger(__name__).warning("call_llm failed: %s", exc)
            return None
    else:
        decision = {"tp_mult": 2.0, "sl_mult": 1.0}

    atr = indicators.get("atr")
    pip_size = 0.01 if env_loader.get_env("DEFAULT_PAIR", "USD_JPY").endswith("_JPY") else 0.0001
    atr_val = float(atr[-1]) if atr else 0.0
    tp_pips = atr_val / pip_size * float(decision.get("tp_mult", 2.0))
    sl_pips = atr_val / pip_size * float(decision.get("sl_mult", 1.0))

    manager = get_order_manager()
    instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    side = signal.get("side", "long")
    lot = int(decision.get("lot", 1))
    manager.place_market_with_tp_sl(instrument, lot, side, tp_pips, sl_pips)

    try:
        metrics_publisher.incr_metric("tech_entry_total", 1, {"mode": mode})
    except Exception:
        pass

    return {"side": side, "tp": tp_pips, "sl": sl_pips, "mode": mode}


__all__ = ["run_cycle"]

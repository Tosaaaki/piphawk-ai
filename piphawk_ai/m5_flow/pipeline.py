"""M5 即エントリー × AI TP チューナー パイプライン."""
from __future__ import annotations

from backend.orders import get_order_manager
from backend.utils import env_loader

from piphawk_ai.tech_arch.market_context import build as build_context
from piphawk_ai.tech_arch.indicator_engine import compute

from .market_classifier import classify_market
from .risk_filters import check_all
from .m5_entry import detect_entry
from .ai_decision import call_llm


def run_cycle() -> dict | None:
    """フローを1回実行して結果を返す."""
    from monitoring import metrics_publisher
    ctx = build_context()
    candles = ctx.candles[-3:]
    indicators = compute(candles)
    mode = classify_market(indicators)

    signal = detect_entry(mode, candles, indicators)
    if not signal:
        return None

    atr_series = indicators.get("atr")
    atr = None
    if atr_series is not None and len(atr_series):
        atr = float(atr_series.iloc[-1]) if hasattr(atr_series, "iloc") else float(atr_series[-1])

    if not check_all(ctx.spread, atr, getattr(ctx, "account", None), signal["side"]):
        return None

    payload = {
        "pair": env_loader.get_env("DEFAULT_PAIR", "USD_JPY"),
        "mode": mode,
        "signal": signal,
        "m5_indicators": {k: float(v.iloc[-1]) if hasattr(v, "iloc") else float(v[-1]) for k, v in indicators.items() if v is not None and len(v)},
        "atr_pips": atr,
    }
    decision = call_llm(payload)
    if not decision or decision.get("decision") != "GO":
        return None

    tp_mult = float(decision.get("tp_mult", 1.0))
    sl_mult = float(decision.get("sl_mult", 1.0))
    if atr is None:
        return None
    tp = atr * tp_mult
    sl = atr * sl_mult

    manager = get_order_manager()
    instrument = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
    manager.place_market_with_tp_sl(instrument, 1, signal["side"], tp, sl)

    try:
        metrics_publisher.incr_metric("m5_ai_entry_total", 1, {"mode": mode})
    except Exception:
        pass

    return {"side": signal["side"], "tp": tp, "sl": sl, "mode": mode}


__all__ = ["run_cycle"]

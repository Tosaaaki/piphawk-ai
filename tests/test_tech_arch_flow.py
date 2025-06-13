import types
import sys

sys.modules.setdefault(
    "monitoring.metrics_publisher",
    types.SimpleNamespace(incr_metric=lambda *a, **k: None),
)

from piphawk_ai.tech_arch.pipeline import run_cycle
from piphawk_ai.tech_arch.market_context import MarketContext


def test_run_cycle(monkeypatch):
    monkeypatch.setenv("DEFAULT_PAIR", "USD_JPY")
    monkeypatch.setenv("OANDA_API_KEY", "x")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "x")

    ctx = MarketContext(
        candles=[
            {"mid": {"c": "1.0", "h": "1.0", "l": "1.0"}, "complete": True},
            {"mid": {"c": "1.02", "h": "1.03", "l": "1.01"}, "complete": True},
        ],
        tick={"prices": [{"bids": [{"price": "1.02"}], "asks": [{"price": "1.03"}]}]},
        spread=0.00005,
        account={"NAV": "1000", "marginAvailable": "100"},
    )

    monkeypatch.setattr("piphawk_ai.tech_arch.market_context.build", lambda: ctx)
    monkeypatch.setattr("piphawk_ai.tech_arch.pipeline.build_context", lambda: ctx)

    indicators = {
        "atr": [0.0005, 0.0005],
        "adx": [30],
        "ema_fast": [1.02],
        "ema_slow": [1.00],
        "bb_upper": [1.05],
        "bb_lower": [0.95],
    }
    monkeypatch.setattr(
        "piphawk_ai.tech_arch.indicator_engine.compute", lambda _c: indicators
    )
    monkeypatch.setattr(
        "piphawk_ai.tech_arch.pipeline.compute", lambda _c: indicators
    )

    monkeypatch.setattr(
        "piphawk_ai.tech_arch.ai_decision.call_llm",
        lambda mode, signal, ind: {"go": True, "tp_mult": 2.0, "sl_mult": 1.0},
    )
    monkeypatch.setattr(
        "piphawk_ai.tech_arch.pipeline.call_llm",
        lambda mode, signal, ind: {"go": True, "tp_mult": 2.0, "sl_mult": 1.0},
    )

    calls = []
    fake_mgr = types.SimpleNamespace(
        place_market_with_tp_sl=lambda inst, lot, side, tp, sl: calls.append((inst, side, tp, sl))
    )
    monkeypatch.setattr("backend.orders.get_order_manager", lambda: fake_mgr)
    monkeypatch.setattr("piphawk_ai.tech_arch.pipeline.get_order_manager", lambda: fake_mgr)

    plan = run_cycle()
    assert plan is not None
    assert calls
    assert plan["tp"] > plan["sl"]


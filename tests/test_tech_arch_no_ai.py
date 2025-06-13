import sys
import types

sys.modules.setdefault(
    "monitoring.metrics_publisher",
    types.SimpleNamespace(incr_metric=lambda *a, **k: None),
)

from piphawk_ai.tech_arch.market_context import MarketContext
from piphawk_ai.tech_arch.pipeline import run_cycle


def _setup_common(monkeypatch):
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
    monkeypatch.setattr("piphawk_ai.tech_arch.pipeline.compute", lambda _c: indicators)
    return ctx


def test_run_cycle_default_when_no_ai(monkeypatch):
    monkeypatch.setenv("ENTRY_USE_AI", "false")
    monkeypatch.setenv("DEFAULT_PAIR", "USD_JPY")
    monkeypatch.setenv("OANDA_API_KEY", "x")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "x")

    _setup_common(monkeypatch)

    monkeypatch.setattr(
        "piphawk_ai.tech_arch.ai_decision.call_llm",
        lambda *a, **k: {"go": True},
    )
    monkeypatch.setattr(
        "piphawk_ai.tech_arch.pipeline.call_llm",
        lambda *a, **k: {"go": True},
    )

    calls = []
    fake_mgr = types.SimpleNamespace(
        place_market_with_tp_sl=lambda inst, lot, side, tp, sl: calls.append((inst, side, tp, sl))
    )
    monkeypatch.setattr("backend.orders.get_order_manager", lambda: fake_mgr)
    monkeypatch.setattr("piphawk_ai.tech_arch.pipeline.get_order_manager", lambda: fake_mgr)

    plan = run_cycle()
    assert plan == {"side": "long", "tp": 0.1, "sl": 0.05, "mode": "trend"}
    assert calls


def test_run_cycle_fallback_on_invalid_ai(monkeypatch):
    monkeypatch.setenv("ENTRY_USE_AI", "true")
    monkeypatch.setenv("DEFAULT_PAIR", "USD_JPY")
    monkeypatch.setenv("OANDA_API_KEY", "x")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "x")

    _setup_common(monkeypatch)

    def broken_call_llm(*_a, **_k):
        raise ValueError("invalid json")

    monkeypatch.setattr("piphawk_ai.tech_arch.ai_decision.call_llm", broken_call_llm)
    monkeypatch.setattr("piphawk_ai.tech_arch.pipeline.call_llm", broken_call_llm)

    fake_mgr = types.SimpleNamespace(place_market_with_tp_sl=lambda *a, **k: None)
    monkeypatch.setattr("backend.orders.get_order_manager", lambda: fake_mgr)
    monkeypatch.setattr("piphawk_ai.tech_arch.pipeline.get_order_manager", lambda: fake_mgr)

    assert run_cycle() is None

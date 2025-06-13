import sys
import types
import pytest

# kafka, openai, pandas をスタブ
sys.modules.setdefault("kafka", types.ModuleType("kafka"))
openai_stub = types.ModuleType("openai")
openai_stub.OpenAI = object
openai_stub.APIError = Exception
sys.modules.setdefault("openai", openai_stub)
sys.modules.setdefault("pandas", types.ModuleType("pandas"))
monitoring_pkg = types.ModuleType("monitoring")
metrics_stub = types.SimpleNamespace(incr_metric=lambda *a, **k: None)
monitoring_pkg.metrics_publisher = metrics_stub
sys.modules.setdefault("monitoring", monitoring_pkg)
sys.modules.setdefault("monitoring.metrics_publisher", metrics_stub)

from piphawk_ai.m5_flow import pipeline as m5pipe


def test_run_cycle(monkeypatch):
    ctx = types.SimpleNamespace(
        candles=[
            {"h": "1.1", "l": "1.0", "o": "1.0", "c": "1.05"},
            {"h": "1.2", "l": "1.0", "o": "1.0", "c": "1.15"},
            {"h": "1.3", "l": "1.1", "o": "1.15", "c": "1.25"},
        ],
        tick={},
        spread=0.0005,
        account={"NAV": 100, "marginAvailable": 80},
    )

    monkeypatch.setattr(m5pipe, "build_context", lambda: ctx)
    monkeypatch.setattr(
        m5pipe,
        "compute",
        lambda c: {
            "atr": [0.01, 0.01, 0.01],
            "ema_fast": [1.2],
            "ema_slow": [1.1],
            "bb_upper": [1.3],
            "bb_lower": [1.0],
            "adx": [30.0],
        },
    )
    monkeypatch.setattr(m5pipe, "call_llm", lambda p: {"decision": "GO", "tp_mult": 2, "sl_mult": 1})
    order = {}
    monkeypatch.setattr(
        m5pipe,
        "get_order_manager",
        lambda: types.SimpleNamespace(place_market_with_tp_sl=lambda i, u, s, tp, sl: order.update({"side": s, "tp": tp, "sl": sl})),
    )

    result = m5pipe.run_cycle()
    assert result is not None
    assert result["side"] == "long"
    assert order["tp"] == pytest.approx(0.02)
    assert order["sl"] == pytest.approx(0.01)


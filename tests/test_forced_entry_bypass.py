import importlib
import sys
import types

import backend.strategy.entry_logic as el


def setup_stub(monkeypatch, force=False):
    # stub openai_analysis module
    oa = types.ModuleType("backend.strategy.openai_analysis")
    oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "no"}, "risk": {}}
    oa.is_entry_blocked_by_recent_candles = lambda *a, **k: False
    monkeypatch.setitem(sys.modules, "backend.strategy.openai_analysis", oa)

    # stub dependencies
    monkeypatch.setattr(el.order_manager, "enter_trade", lambda *a, **k: True)
    monkeypatch.setattr(el, "log_trade", lambda *a, **k: None)
    monkeypatch.setattr(el, "is_extension", lambda *a, **k: False)
    monkeypatch.setattr(el, "false_break_skip", lambda *a, **k: False)
    monkeypatch.setattr("backend.risk_manager.cost_guard", lambda *a, **k: True)
    monkeypatch.setattr("piphawk_ai.analysis.signal_filter.is_multi_tf_aligned", lambda *a, **k: None)

    monkeypatch.setenv("STRICT_TF_ALIGN", "true")
    monkeypatch.setenv("FALLBACK_FORCE_ON_NO_SIDE", "true" if force else "false")

    importlib.reload(el)

    kwargs = dict(
        indicators={},
        candles=[],
        market_data={"prices": [{"bids": [{"price": "1"}], "asks": [{"price": "1.01"}]}]},
        market_cond={"market_condition": "trend", "trend_direction": "long"},
        candles_dict={"M5": []},
        tf_align="M5",
        indicators_multi={"M5": {}},
    )
    return kwargs


def test_forced_entry_bypass(monkeypatch):
    kwargs = setup_stub(monkeypatch, force=False)
    assert el.process_entry(**kwargs) is False

    kwargs = setup_stub(monkeypatch, force=True)
    assert el.process_entry(**kwargs) is True


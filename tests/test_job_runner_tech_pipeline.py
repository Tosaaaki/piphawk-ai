import os
import types
import importlib
import sys

os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")
os.environ.setdefault("OPENAI_API_KEY", "x")

def test_job_runner_tech_pipeline(monkeypatch):
    monkeypatch.setenv("USE_VOTE_ARCH", "true")
    monkeypatch.setenv("USE_VOTE_PIPELINE", "false")

    sf_mod = types.ModuleType("piphawk_ai.analysis.signal_filter")
    sf_mod.is_multi_tf_aligned = lambda *a, **k: True
    sys.modules["piphawk_ai.analysis.signal_filter"] = sf_mod
    kafka_mod = types.ModuleType("kafka")
    kafka_mod.KafkaProducer = lambda *a, **k: None
    sys.modules.setdefault("kafka", kafka_mod)
    prom_mod = types.ModuleType("prometheus_client")
    prom_mod.Gauge = lambda *a, **k: None
    sys.modules.setdefault("prometheus_client", prom_mod)
    mp_mod = types.ModuleType("monitoring.metrics_publisher")
    mp_mod.publish = lambda *a, **k: None
    mp_mod.record_latency = lambda *a, **k: None
    sys.modules["monitoring.metrics_publisher"] = mp_mod
    notif_mod = types.ModuleType("backend.utils.notification")
    notif_mod.send_line_message = lambda *a, **k: None
    sys.modules["backend.utils.notification"] = notif_mod
    strat_mod = types.ModuleType("strategies")
    strat_mod.ScalpStrategy = lambda *a, **k: None
    strat_mod.TrendStrategy = lambda *a, **k: None
    strat_mod.StrongTrendStrategy = lambda *a, **k: None
    strat_mod.StrategySelector = lambda *a, **k: types.SimpleNamespace(select=lambda ctx: types.SimpleNamespace(name="scalp"))
    sys.modules["strategies"] = strat_mod
    scb_mod = types.ModuleType("strategies.context_builder")
    scb_mod.build_context = lambda *a, **k: {}
    scb_mod.recent_strategy_performance = lambda: {}
    sys.modules["strategies.context_builder"] = scb_mod
    rc_mod = types.ModuleType("piphawk_ai.runner.core")
    rc_mod.main = lambda: None
    sys.modules["piphawk_ai.runner.core"] = rc_mod
    sys.modules.setdefault("piphawk_ai.runner.entry", types.ModuleType("piphawk_ai.runner.entry"))
    sys.modules.setdefault("piphawk_ai.ai.macro_analyzer", types.ModuleType("piphawk_ai.ai.macro_analyzer"))
    sys.modules["piphawk_ai.ai.macro_analyzer"].MacroAnalyzer = lambda *a, **k: None
    sys.modules.setdefault("httpx", types.ModuleType("httpx"))
    import backend.scheduler.job_runner as jr_mod
    importlib.reload(jr_mod)

    monkeypatch.setattr(jr_mod, "fetch_tick_data", lambda *a, **k: {"prices": [{"bids": [{"price": "1"}], "asks": [{"price": "1.1"}], "tradeable": True}]})
    monkeypatch.setattr(
        jr_mod,
        "fetch_multiple_timeframes",
        lambda *a, **k: {"M5": [{"mid": {"c": "1", "h": "1", "l": "1"}, "complete": True, "volume": 1}], "M1": []},
    )
    monkeypatch.setattr(
        jr_mod,
        "calculate_indicators_multi",
        lambda *a, **k: {
            "M5": {
                "adx": [30],
                "ema_fast": [1.1],
                "ema_slow": [1.0],
                "bb_upper": [1.2],
                "bb_lower": [0.8],
                "atr": [0.05],
            }
        },
    )
    monkeypatch.setattr(jr_mod, "analyze_higher_tf", lambda *a, **k: {})
    monkeypatch.setattr(jr_mod, "decide_trade_mode_detail", lambda *a, **k: ("scalp", 0.0, []))
    monkeypatch.setattr(jr_mod, "recent_strategy_performance", lambda: {})
    monkeypatch.setattr(jr_mod, "build_context", lambda *a, **k: {})
    monkeypatch.setattr(jr_mod, "check_current_position", lambda *a, **k: None)
    monkeypatch.setattr(jr_mod, "follow_breakout", lambda *a, **k: None)
    monkeypatch.setattr(jr_mod, "filter_pre_ai", lambda *a, **k: False)
    monkeypatch.setattr(jr_mod, "detect_climax_reversal", lambda *a, **k: None)
    monkeypatch.setattr(jr_mod, "counter_trend_block", lambda *a, **k: False)
    monkeypatch.setattr(jr_mod, "consecutive_lower_lows", lambda *a, **k: False)
    monkeypatch.setattr(jr_mod, "consecutive_higher_highs", lambda *a, **k: False)
    monkeypatch.setattr(jr_mod, "pass_entry_filter", lambda *a, **k: True)
    monkeypatch.setattr(jr_mod, "pass_exit_filter", lambda *a, **k: True)
    monkeypatch.setattr(jr_mod, "instrument_is_tradeable", lambda *a, **k: True)
    monkeypatch.setattr(jr_mod, "update_oanda_trades", lambda *a, **k: None)
    monkeypatch.setattr(jr_mod, "maybe_cleanup", lambda: None)
    monkeypatch.setattr(jr_mod, "metrics_publisher", types.SimpleNamespace(publish=lambda *a, **k: None))
    monkeypatch.setattr(jr_mod, "PerfTimer", lambda *_a, **_k: types.SimpleNamespace(stop=lambda: None))
    monkeypatch.setattr(jr_mod, "time", types.SimpleNamespace(sleep=lambda *_: None, time=lambda: 0))
    monkeypatch.setattr(jr_mod, "get_margin_used", lambda: 0)

    called = {}
    monkeypatch.setattr(jr_mod, "tech_run_cycle", lambda: called.setdefault("x", True))

    jr = jr_mod.JobRunner(interval_seconds=0)
    jr.run()

    assert called

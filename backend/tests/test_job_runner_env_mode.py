import os
import sys
import types
import importlib
import unittest


class TestJobRunnerEnvMode(unittest.TestCase):
    def setUp(self):
        self._mods = []

        def add(name: str, mod: types.ModuleType):
            sys.modules[name] = mod
            self._mods.append(name)

        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        pd = types.ModuleType("pandas")
        pd.Series = lambda *a, **k: None
        add("pandas", pd)
        dz = types.ModuleType("dotenv")
        dz.load_dotenv = lambda *a, **k: None
        add("dotenv", dz)

        openai_stub = types.ModuleType("openai")
        openai_stub.OpenAI = lambda *a, **k: None
        openai_stub.APIError = Exception
        add("openai", openai_stub)

        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = "gpt"
        oc.set_call_limit = lambda *_a, **_k: None
        add("backend.utils.openai_client", oc)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "no"}, "risk": {}}
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        add("backend.market_data.tick_fetcher", types.ModuleType("backend.market_data.tick_fetcher"))
        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: None
        add("backend.market_data.candle_fetcher", types.ModuleType("backend.market_data.candle_fetcher"))
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = lambda *a, **k: {}

        ind_mod = types.ModuleType("backend.indicators.calculate_indicators")
        ind_mod.calculate_indicators = lambda *a, **k: {}
        ind_mod.calculate_indicators_multi = lambda *a, **k: {}
        add("backend.indicators.calculate_indicators", ind_mod)

        el = types.ModuleType("backend.strategy.entry_logic")
        el.process_entry = lambda *a, **k: None
        el._pending_limits = {}
        add("backend.strategy.entry_logic", el)
        ex = types.ModuleType("backend.strategy.exit_logic")
        ex.process_exit = lambda *a, **k: None
        add("backend.strategy.exit_logic", ex)
        ex_ai = types.ModuleType("backend.strategy.exit_ai_decision")
        ex_ai.evaluate = lambda *a, **k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        add("backend.strategy.exit_ai_decision", ex_ai)

        pm = types.ModuleType("backend.orders.position_manager")
        pm.check_current_position = lambda *a, **k: None
        pm.get_margin_used = lambda *a, **k: None
        pm.get_position_details = lambda *a, **k: None
        add("backend.orders.position_manager", pm)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self, *a, **k):
                pass
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        sf = types.ModuleType("backend.strategy.signal_filter")
        sf.pass_entry_filter = lambda *a, **k: True
        sf.filter_pre_ai = lambda *a, **k: False
        sf.detect_climax_reversal = lambda *a, **k: None
        sf.counter_trend_block = lambda *a, **k: False
        sf.consecutive_lower_lows = lambda *a, **k: False
        sf.consecutive_higher_highs = lambda *a, **k: False
        sf.pass_exit_filter = lambda *a, **k: True
        add("backend.strategy.signal_filter", sf)
        add("analysis.signal_filter", types.ModuleType("analysis.signal_filter"))
        sys.modules["analysis.signal_filter"].is_multi_tf_aligned = lambda *a, **k: True

        ht = types.ModuleType("backend.strategy.higher_tf_analysis")
        ht.analyze_higher_tf = lambda *a, **k: {}
        add("backend.strategy.higher_tf_analysis", ht)

        pattern = types.ModuleType("backend.strategy.pattern_scanner")
        pattern.scan = lambda *a, **k: {}
        pattern.PATTERN_DIRECTION = {}
        add("backend.strategy.pattern_scanner", pattern)

        momentum = types.ModuleType("backend.strategy.momentum_follow")
        momentum.follow_breakout = lambda *a, **k: True
        add("backend.strategy.momentum_follow", momentum)

        uot = types.ModuleType("backend.logs.update_oanda_trades")
        uot.update_oanda_trades = lambda *a, **k: None
        uot.fetch_trade_details = lambda *a, **k: {}
        add("backend.logs.update_oanda_trades", uot)

        rd = types.ModuleType("analysis.regime_detector")
        class DummyRD:
            def update(self, *a, **k):
                return {"transition": False}
        rd.RegimeDetector = DummyRD
        add("analysis.regime_detector", rd)

        notif = types.ModuleType("backend.utils.notification")
        notif.send_line_message = lambda *a, **k: None
        add("backend.utils.notification", notif)

        lm = types.ModuleType("backend.logs.log_manager")
        lm.log_entry_skip = lambda *a, **k: None
        lm.log_ai_decision = lambda *a, **k: None
        add("backend.logs.log_manager", lm)

        tl = types.ModuleType("backend.logs.trade_logger")
        tl.log_trade = lambda *a, **k: None
        tl.ExitReason = type("ExitReason", (), {})
        add("backend.logs.trade_logger", tl)

        comp = types.ModuleType("signals.composite_mode")
        comp.decide_trade_mode = lambda *a, **k: "trend_follow"
        add("signals.composite_mode", comp)

        self.calls = []
        params = types.ModuleType("config.params_loader")
        def load_params(path="config/strategy.yml", *a, **k):
            self.calls.append(path)
        params.load_params = load_params
        add("config.params_loader", params)

        os.environ["SCALP_MODE"] = "false"
        os.environ["PIP_SIZE"] = "0.01"
        os.environ["OANDA_API_KEY"] = "dummy"
        os.environ["OANDA_ACCOUNT_ID"] = "dummy"
        os.environ["OPENAI_API_KEY"] = "dummy"

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        self.jr = jr.JobRunner(interval_seconds=1)

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        for key in [
            "SCALP_MODE",
            "PIP_SIZE",
            "OANDA_API_KEY",
            "OANDA_ACCOUNT_ID",
        ]:
            os.environ.pop(key, None)

    def test_reload_skipped_when_mode_same(self):
        self.assertEqual(self.jr.trade_mode, "trend_follow")
        self.assertEqual(self.jr.current_params_file, "config/trend.yml")
        before = len(self.calls)
        self.jr.reload_params_for_mode("trend_follow")
        self.assertEqual(len(self.calls), before)
        self.assertEqual(self.jr.trade_mode, "trend_follow")
        self.assertEqual(self.jr.current_params_file, "config/trend.yml")


if __name__ == "__main__":
    unittest.main()

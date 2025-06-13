import importlib
import os
import sys
import types
import unittest


class TestJobRunnerRestoreMode(unittest.TestCase):
    def setUp(self):
        self._mods = []

        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        add("requests", types.ModuleType("requests"))
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = lambda *a, **k: None
        add("pandas", pandas_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)

        om_mod = types.ModuleType("backend.orders.order_manager")
        om_mod.OrderManager = lambda *a, **k: None
        add("backend.orders.order_manager", om_mod)

        pm_mod = types.ModuleType("backend.orders.position_manager")
        pm_mod.get_position_details = lambda *a, **k: None
        pm_mod.check_current_position = lambda *a, **k: None
        pm_mod.get_margin_used = lambda *a, **k: None
        add("backend.orders.position_manager", pm_mod)

        for name in [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.entry_logic",
            "backend.strategy.exit_logic",
            "backend.strategy.signal_filter",
            "backend.strategy.higher_tf_analysis",
            "backend.utils.notification",
            "backend.logs.update_oanda_trades",
            "backend.strategy.pattern_scanner",
            "backend.strategy.momentum_follow",
        ]:
            mod = types.ModuleType(name)
            add(name, mod)

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: {}
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = (
            lambda *a, **k: {}
        )
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators_multi = (
            lambda *a, **k: {}
        )
        sys.modules["backend.strategy.entry_logic"].process_entry = lambda *a, **k: None
        sys.modules["backend.strategy.entry_logic"]._pending_limits = {}
        sys.modules["backend.strategy.exit_logic"].process_exit = lambda *a, **k: None
        sys.modules["backend.strategy.signal_filter"].pass_entry_filter = lambda *a, **k: True
        sys.modules["backend.strategy.signal_filter"].pass_exit_filter = lambda *a, **k: True
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}
        sys.modules["backend.utils.notification"].send_line_message = lambda *a, **k: None
        sys.modules["backend.logs.update_oanda_trades"].update_oanda_trades = lambda *a, **k: None
        sys.modules["backend.logs.update_oanda_trades"].fetch_trade_details = lambda *a, **k: {}
        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = "gpt"
        oc.set_call_limit = lambda *_a, **_k: None
        add("backend.utils.openai_client", oc)
        sys.modules["backend.strategy.pattern_scanner"].PATTERN_DIRECTION = {}
        sys.modules["backend.strategy.momentum_follow"].follow_breakout = lambda *a, **k: True

        os.environ["PIP_SIZE"] = "0.01"
        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        self.jr = jr

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        os.environ.pop("PIP_SIZE", None)
        os.environ.pop("SCALP_MODE", None)

    def test_restore_scalp(self):
        os.environ["SCALP_MODE"] = "true"
        importlib.reload(self.jr)
        runner = self.jr.JobRunner()
        self.assertEqual(runner.trade_mode, "scalp")
        self.assertEqual(runner.current_params_file, "config/scalp_params.yml")

    def test_restore_trend(self):
        os.environ["SCALP_MODE"] = "false"
        importlib.reload(self.jr)
        runner = self.jr.JobRunner()
        self.assertEqual(runner.trade_mode, "trend_follow")
        self.assertEqual(runner.current_params_file, "config/trend.yml")


if __name__ == "__main__":
    unittest.main()

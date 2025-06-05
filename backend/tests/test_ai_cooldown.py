import os
import sys
import types
import importlib
import unittest

class TestGetAICooldownSec(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        self._added_modules = []

        def add_module(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added_modules.append(name)

        class FakeSeries(list):
            pass

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add_module("pandas", pandas_stub)
        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add_module("openai", openai_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add_module("dotenv", dotenv_stub)
        add_module("requests", types.ModuleType("requests"))
        add_module("numpy", types.ModuleType("numpy"))

        import backend.strategy.openai_analysis as oa
        importlib.reload(oa)
        self.oa = oa

    def tearDown(self):
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)

    def test_nested_units_long_or_short(self):
        self.assertEqual(
            self.oa.get_ai_cooldown_sec({"long": {"units": "1"}}),
            self.oa.AI_COOLDOWN_SEC_FLAT,
        )
        self.assertEqual(
            self.oa.get_ai_cooldown_sec({"short": {"units": "-2"}}),
            self.oa.AI_COOLDOWN_SEC_FLAT,
        )

    def test_no_position_returns_open_cooldown(self):
        self.assertEqual(
            self.oa.get_ai_cooldown_sec({}),
            self.oa.AI_COOLDOWN_SEC_OPEN,
        )
        self.assertEqual(
            self.oa.get_ai_cooldown_sec(None),
            self.oa.AI_COOLDOWN_SEC_OPEN,
        )


class TestRegimeCooldownReset(unittest.TestCase):
    def setUp(self):
        self._mods = []

        def add(name: str, mod: types.ModuleType):
            sys.modules[name] = mod
            self._mods.append(name)

        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        add("pandas", types.ModuleType("pandas"))
        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        dz = types.ModuleType("dotenv")
        dz.load_dotenv = lambda *a, **k: None
        add("dotenv", dz)
        openai_stub = types.ModuleType("openai")
        class DummyClient:
            def __init__(self, *a, **k):
                pass
        openai_stub.OpenAI = DummyClient
        openai_stub.APIError = Exception
        add("openai", openai_stub)
        oc = types.ModuleType("backend.utils.openai_client")
        oc.ask_openai = lambda *a, **k: {}
        oc.AI_MODEL = "gpt"
        add("backend.utils.openai_client", oc)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "no"}, "risk": {}}
        oa.should_convert_limit_to_market = lambda *_a, **_k: False
        oa.evaluate_exit = lambda *_a, **_k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def update_trade_sl(self, *a, **k):
                return {}
            def enter_trade(self, *a, **k):
                return {}
            def cancel_order(self, *a, **k):
                pass
            def place_market_order(self, *a, **k):
                pass
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        upd = types.ModuleType("backend.logs.update_oanda_trades")
        upd.update_oanda_trades = lambda *a, **k: (_ for _ in ()).throw(SystemExit())
        upd.fetch_trade_details = lambda *a, **k: {}
        add("backend.logs.update_oanda_trades", upd)

        stub_names = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.exit_logic",
            "backend.orders.position_manager",
            "backend.strategy.signal_filter",
            "backend.strategy.higher_tf_analysis",
            "backend.utils.notification",
            "backend.strategy.pattern_scanner",
        ]
        for name in stub_names:
            mod = types.ModuleType(name)
            add(name, mod)

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: {
            "prices": [{"bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}], "tradeable": True}]
        }
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = lambda *a, **k: {
            "M5": [], "M1": [], "H1": [], "H4": [], "D": []
        }
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators_multi = lambda *a, **k: {
            "M5": {}, "M1": {}, "H1": {}, "H4": {}, "D": {}
        }
        sys.modules["backend.strategy.exit_logic"].process_exit = lambda *a, **k: None
        sys.modules["backend.orders.position_manager"].check_current_position = lambda *a, **k: None
        sys.modules["backend.strategy.signal_filter"].pass_entry_filter = lambda *a, **k: True
        sys.modules["backend.strategy.signal_filter"].pass_exit_filter = lambda *a, **k: True
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}
        sys.modules["backend.utils.notification"].send_line_message = lambda *a, **k: None
        sys.modules["backend.strategy.pattern_scanner"].scan = lambda *a, **k: {}

        rd_mod = types.ModuleType("analysis.regime_detector")
        class DummyRD:
            def update(self, tick):
                return {"transition": True}
        rd_mod.RegimeDetector = DummyRD
        add("analysis.regime_detector", rd_mod)

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        jr.instrument_is_tradeable = lambda *_a, **_k: True
        self.runner = jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: (_ for _ in ()).throw(SystemExit())

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)

    def test_transition_resets_last_ai_call(self):
        from datetime import datetime
        self.runner.last_ai_call = datetime.now()
        with self.assertRaises(SystemExit):
            self.runner.run()
        self.assertEqual(self.runner.last_ai_call, datetime.min)

if __name__ == "__main__":
    unittest.main()

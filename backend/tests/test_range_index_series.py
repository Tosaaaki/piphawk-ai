import os
import sys
import types
import importlib
import unittest

class FakeSeries:
    def __init__(self, data):
        self._data = list(data)
        class _ILoc:
            def __init__(self, outer):
                self._outer = outer
            def __getitem__(self, idx):
                return self._outer._data[idx]
        self.iloc = _ILoc(self)
    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self._data[idx]
        if isinstance(idx, int) and idx < 0:
            raise KeyError(idx)
        return self._data[idx]

class TestSeriesHandling(unittest.TestCase):
    def setUp(self):
        os.environ.setdefault("OPENAI_API_KEY", "dummy")
        os.environ.setdefault("BE_TRIGGER_PIPS", "10")

        # Keep track of modules we stub so they can be cleaned up in tearDown
        self._added_modules: list[str] = []

        def add_module(name: str, module: types.ModuleType):
            if name not in sys.modules:
                sys.modules[name] = module
                self._added_modules.append(name)

        add_module("pandas", types.ModuleType("pandas"))
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

        stub_modules = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.entry_logic",
            "backend.strategy.exit_logic",
            "backend.orders.position_manager",
            "backend.orders.order_manager",
            "backend.strategy.signal_filter",
            "backend.strategy.higher_tf_analysis",
            "backend.utils.notification",
        ]
        for name in stub_modules:
            mod = types.ModuleType(name)
            add_module(name, mod)

        # provide minimal attributes for imported names
        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: None
        sys.modules["backend.market_data.candle_fetcher"].fetch_candles = lambda *a, **k: []
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = lambda *a, **k: {"M5": []}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators_multi = lambda *a, **k: {"M5": {}}
        sys.modules["backend.strategy.entry_logic"].process_entry = lambda *a, **k: None
        sys.modules["backend.strategy.entry_logic"]._pending_limits = {}
        sys.modules["backend.strategy.exit_logic"].process_exit = lambda *a, **k: None
        sys.modules["backend.orders.position_manager"].check_current_position = lambda *a, **k: None
        class DummyOrderMgr:
            pass
        sys.modules["backend.orders.order_manager"].OrderManager = DummyOrderMgr
        sys.modules["backend.strategy.signal_filter"].pass_entry_filter = lambda *a, **k: True
        sys.modules["backend.strategy.signal_filter"].pass_exit_filter = lambda *a, **k: True
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: None
        sys.modules["backend.utils.notification"].send_line_message = lambda *a, **k: None
        import backend.strategy.openai_analysis as oa
        import backend.scheduler.job_runner as jr
        importlib.reload(oa)
        importlib.reload(jr)
        self.oa = oa
        self.jr = jr

    def tearDown(self):
        # Remove any modules we added during setUp to keep sys.modules clean
        for name in getattr(self, "_added_modules", []):
            sys.modules.pop(name, None)

    def test_get_trade_plan_range_index(self):
        self.oa.ask_openai = lambda *a, **k: '{"entry": {"side": "no"}}'
        indicators = {
            "bb_upper": FakeSeries([1, 2, 3]),
            "bb_lower": FakeSeries([0, 1, 2]),
            "atr": FakeSeries([1, 1, 1]),
            "adx": FakeSeries([25, 25, 25]),
        }
        plan = self.oa.get_trade_plan({}, {"M5": indicators}, {"M5": []})
        self.assertIn("entry", plan)
        self.assertEqual(plan.get("risk"), {})

    def test_build_exit_context_range_index(self):
        indicators = {
            "atr": FakeSeries([1, 2]),
            "rsi": FakeSeries([30, 40]),
            "ema_slope": FakeSeries([0.1, 0.2]),
        }
        position = {
            "long": {"units": "1", "averagePrice": "1.0"},
            "unrealizedPL": "0",
            "instrument": "EUR_USD",
        }
        tick = {"prices": [{"bids": [{"price": "1"}], "asks": [{"price": "2"}]}]}
        context = self.jr.build_exit_context(position, tick, indicators, {})
        self.assertEqual(context["atr_pips"], 2)
        self.assertEqual(context["rsi"], 40)
        self.assertEqual(context["ema_slope"], 0.2)

if __name__ == "__main__":
    unittest.main()

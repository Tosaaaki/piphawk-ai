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
        return self._data[idx]
    def __len__(self):
        return len(self._data)

class TestTpReduction(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        add("requests", types.ModuleType("requests"))
        add("numpy", types.ModuleType("numpy"))
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.calls = []
            def adjust_tp_sl(self, instrument, trade_id, new_tp=None, new_sl=None):
                self.calls.append((instrument, trade_id, new_tp, new_sl))
                return {}
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

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

        stub_names = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.exit_logic",
            "backend.orders.position_manager",
            "backend.strategy.signal_filter",
            "backend.strategy.higher_tf_analysis",
            "backend.utils.notification",
            "backend.logs.update_oanda_trades",
            "backend.strategy.pattern_scanner",
        ]
        for name in stub_names:
            mod = types.ModuleType(name)
            add(name, mod)

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: None
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = lambda *a, **k: {"M5": []}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators_multi = lambda *a, **k: {"M5": {}}
        sys.modules["backend.strategy.exit_logic"].process_exit = lambda *a, **k: None
        sys.modules["backend.orders.position_manager"].check_current_position = lambda *a, **k: None
        sys.modules["backend.strategy.signal_filter"].pass_entry_filter = lambda *a, **k: True
        sys.modules["backend.strategy.signal_filter"].pass_exit_filter = lambda *a, **k: True
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}
        sys.modules["backend.utils.notification"].send_line_message = lambda *a, **k: None
        sys.modules["backend.strategy.pattern_scanner"].scan = lambda *a, **k: {}
        sys.modules["backend.strategy.pattern_scanner"].PATTERN_DIRECTION = {}

        sys.modules['backend.logs.update_oanda_trades'].update_oanda_trades = lambda *a, **k: None
        sys.modules['backend.logs.update_oanda_trades'].fetch_trade_details = lambda *a, **k: {}

        os.environ["OANDA_ACCOUNT_ID"] = "dummy"
        os.environ["OANDA_API_KEY"] = "dummy"
        os.environ["TP_REDUCTION_ENABLED"] = "true"
        os.environ["TP_REDUCTION_ADX_MAX"] = "20"
        os.environ["TP_REDUCTION_MIN_SEC"] = "0"
        os.environ["TP_REDUCTION_ATR_MULT"] = "1"
        os.environ["PIP_SIZE"] = "0.01"

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        jr.instrument_is_tradeable = lambda instrument: True
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: None
        self.om = jr.order_mgr

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_tp_reduction_called(self):
        pos = {
            "instrument": "USD_JPY",
            "long": {"units": "1", "averagePrice": "1.0", "tradeIDs": ["t1"]},
            "unrealizedPL": "0",
            "entry_time": "2024-01-01T00:00:00Z"
        }
        indicators = {"adx": FakeSeries([15]), "atr": FakeSeries([0.1])}
        self.runner.tp_reduced = False
        self.runner._maybe_reduce_tp(pos, indicators, "long", 0.01)
        self.assertEqual(len(self.om.calls), 1)
        inst, tid, new_tp, _ = self.om.calls[0]
        self.assertEqual(inst, "USD_JPY")
        self.assertEqual(tid, "t1")
        self.assertAlmostEqual(new_tp, 1.1)

if __name__ == "__main__":
    unittest.main()

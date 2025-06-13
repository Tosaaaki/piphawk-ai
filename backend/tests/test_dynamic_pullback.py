import importlib
import os
import sys
import types
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
    def __len__(self):
        return len(self._data)

class TestDynamicPullback(unittest.TestCase):
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

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "long", "mode": "market"}, "risk": {"tp_pips": 10, "sl_pips": 5}}
        oa.get_market_condition = lambda *a, **k: {"market_condition": "trend", "trend_direction": "long"}
        oa.should_convert_limit_to_market = lambda ctx: True
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.enter_called = False
                self.last_params = None
            def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False, with_oco=True):
                self.enter_called = True
                self.last_params = strategy_params
                return {"order_id": "1"}
            def cancel_order(self, oid):
                pass
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)

        oc = types.ModuleType("backend.utils.oanda_client")
        oc.get_pending_entry_order = lambda instrument: {"order_id": "1", "ts": 0}
        add("backend.utils.oanda_client", oc)

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
            "backend.logs.log_manager",
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
        sys.modules["backend.logs.update_oanda_trades"].update_oanda_trades = lambda *a, **k: None
        sys.modules["backend.logs.update_oanda_trades"].fetch_trade_details = lambda *a, **k: {}
        sys.modules["backend.logs.log_manager"].get_db_connection = lambda *a, **k: None
        sys.modules["backend.logs.log_manager"].log_trade = lambda *a, **k: None

        os.environ["PULLBACK_LIMIT_OFFSET_PIPS"] = "2"
        os.environ["PULLBACK_ATR_RATIO"] = "0.5"
        os.environ["PIP_SIZE"] = "0.01"

        import backend.scheduler.job_runner as jr
        import backend.strategy.entry_logic as el
        importlib.reload(el)
        importlib.reload(jr)
        self.el = el
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=1)

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_calculate_offset_atr(self):
        indicators = {"atr": FakeSeries([0.2]), "adx": FakeSeries([40])}
        offset = self.el.calculate_pullback_offset(indicators, {"market_condition": "trend"})
        self.assertGreater(offset, 2)

    def test_switch_limit_to_market(self):
        self.el._pending_limits.clear()
        self.el._pending_limits["a"] = {"instrument": "USD_JPY", "order_id": "1", "ts": 0, "limit_price": 1.0, "side": "long", "retry_count": 0}
        indicators = {"atr": FakeSeries([0.1]), "adx": FakeSeries([40])}
        tick = {"prices": [{"instrument": "USD_JPY", "bids": [{"price": "1.05"}], "asks": [{"price": "1.06"}]}]}
        self.runner._manage_pending_limits("USD_JPY", indicators, [], tick)
        self.assertTrue(self.jr.order_mgr.enter_called)

    def test_calculate_dynamic_pullback(self):
        from backend.strategy.dynamic_pullback import calculate_dynamic_pullback
        indicators = {
            "atr": FakeSeries([0.2]),
            "adx": FakeSeries([25]),
            "noise": FakeSeries([4.0]),
        }
        result = calculate_dynamic_pullback(indicators, 1.2, 1.0)
        self.assertEqual(result, 15.0)

if __name__ == "__main__":
    unittest.main()

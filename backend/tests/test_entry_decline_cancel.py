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
        return self._data[idx]
    def __len__(self):
        return len(self._data)

class TestEntryDeclineCancel(unittest.TestCase):
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
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {}
        oa.should_convert_limit_to_market = lambda ctx: False
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.canceled = []
            def cancel_order(self, oid):
                self.canceled.append(oid)
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        oc = types.ModuleType("backend.utils.oanda_client")
        oc.get_pending_entry_order = lambda instrument: {"order_id": "1", "ts": 0}
        add("backend.utils.oanda_client", oc)

        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)

        upd_mod = types.ModuleType("backend.logs.update_oanda_trades")
        def stop():
            raise SystemExit()
        upd_mod.update_oanda_trades = stop
        upd_mod.fetch_trade_details = lambda *a, **k: {}
        add("backend.logs.update_oanda_trades", upd_mod)

        stub_names = [
            "backend.market_data.tick_fetcher",
            "backend.market_data.candle_fetcher",
            "backend.indicators.calculate_indicators",
            "backend.strategy.exit_logic",
            "backend.orders.position_manager",
            "backend.strategy.signal_filter",
            "backend.strategy.higher_tf_analysis",
            "backend.utils.notification",
        ]
        for name in stub_names:
            mod = types.ModuleType(name)
            add(name, mod)

        sys.modules["backend.market_data.tick_fetcher"].fetch_tick_data = lambda *a, **k: {
            "prices": [{"bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}], "tradeable": True}]
        }
        sys.modules["backend.market_data.candle_fetcher"].fetch_multiple_timeframes = lambda *a, **k: {"M5": []}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators = lambda *a, **k: {}
        sys.modules["backend.indicators.calculate_indicators"].calculate_indicators_multi = lambda *a, **k: {"M5": {}}
        sys.modules["backend.strategy.exit_logic"].process_exit = lambda *a, **k: None
        sys.modules["backend.orders.position_manager"].check_current_position = lambda *a, **k: None
        sys.modules["backend.strategy.signal_filter"].pass_entry_filter = lambda *a, **k: True
        sys.modules["backend.strategy.signal_filter"].pass_exit_filter = lambda *a, **k: True
        sys.modules["backend.strategy.higher_tf_analysis"].analyze_higher_tf = lambda *a, **k: {}
        sys.modules["backend.utils.notification"].send_line_message = lambda *a, **k: None

        os.environ.pop("OANDA_API_KEY", None)
        os.environ.pop("OANDA_ACCOUNT_ID", None)
        os.environ["PIP_SIZE"] = "0.01"

        import backend.scheduler.job_runner as jr
        import backend.strategy.entry_logic as el
        importlib.reload(el)
        importlib.reload(jr)
        self.el = el
        self.jr = jr
        self.runner = jr.JobRunner(interval_seconds=1)
        self.runner._manage_pending_limits = lambda *a, **k: None

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_cancel_on_decline(self):
        self.el._pending_limits.clear()
        self.el._pending_limits["a"] = {"instrument": "USD_JPY", "order_id": "1", "ts": 0, "limit_price": 1.0, "side": "long", "retry_count": 0}
        self.el.process_entry = lambda *a, **k: False
        self.jr.process_entry = self.el.process_entry
        with self.assertRaises(SystemExit):
            self.runner.run()
        self.assertEqual(self.jr.order_mgr.canceled, ["1"])
        self.assertEqual(self.el._pending_limits, {})

if __name__ == "__main__":
    unittest.main()

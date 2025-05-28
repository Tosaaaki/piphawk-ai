import os
import sys
import types
import importlib
import unittest
import datetime

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

class DummyResp:
    def __init__(self):
        self.ok = True
        self.status_code = 200
        self.text = ''
    def json(self):
        return {}
    def raise_for_status(self):
        pass

class TestTrailingCalendar(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")
        os.environ["TRAIL_ENABLED"] = "true"
        os.environ["TRAIL_TRIGGER_PIPS"] = "10"
        os.environ["TRAIL_DISTANCE_PIPS"] = "6"
        os.environ["CALENDAR_VOLATILITY_LEVEL"] = "3"
        os.environ["CALENDAR_VOL_THRESHOLD"] = "3"
        os.environ["CALENDAR_TRAIL_MULTIPLIER"] = "1.5"
        os.environ["EARLY_EXIT_ENABLED"] = "false"
        os.environ["DEFAULT_PAIR"] = "EUR_USD"

        req = types.ModuleType("requests")
        req.post = req.put = req.get = lambda *a, **k: DummyResp()
        add("requests", req)
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv)
        add("numpy", types.ModuleType("numpy"))

        self.position = {}
        pm = types.ModuleType("backend.orders.position_manager")
        pm.get_position_details = lambda *a, **k: self.position
        pm.check_current_position = lambda *a, **k: self.position
        pm.get_margin_used = lambda *a, **k: None
        add("backend.orders.position_manager", pm)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_exit_decision = lambda *a, **k: {"decision": "HOLD", "reason": ""}
        oa.get_market_condition = lambda *a, **k: {}
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "no"}, "risk": {}}
        oa.should_convert_limit_to_market = lambda ctx: False
        class _Resp:
            def __init__(self, d=None):
                self._d = d or {"decision": "HOLD"}
            def as_dict(self):
                return self._d
        oa.evaluate_exit = lambda *a, **k: _Resp()
        oa.EXIT_BIAS_FACTOR = 0.0
        add("backend.strategy.openai_analysis", oa)

        log_stub = types.ModuleType("backend.logs.log_manager")
        log_stub.log_trade = lambda *a, **k: None
        log_stub.log_error = lambda *a, **k: None
        log_stub.get_db_connection = lambda: None
        add("backend.logs.log_manager", log_stub)

        notif = types.ModuleType("backend.utils.notification")
        notif.send_line_message = lambda *a, **k: None
        add("backend.utils.notification", notif)

        import backend.orders.order_manager as om
        importlib.reload(om)

        class DummyOM(om.OrderManager):
            def __init__(self):
                self.calls = []
            def place_trailing_stop(self, trade_id, instrument, distance_pips=None):
                self.calls.append((trade_id, instrument, distance_pips))
                return {}
            def exit_trade(self, *a, **k):
                pass
        self.DummyOM = DummyOM

        import backend.strategy.exit_logic as el
        importlib.reload(el)
        el.order_manager = DummyOM()
        self.el = el

        import backend.scheduler.job_runner as jr
        importlib.reload(jr)
        self.runner = jr.JobRunner(interval_seconds=1)

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)

    def test_trailing_disabled_during_event(self):
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        start = (now.hour + 1) % 24
        end = (start + 1) % 24
        os.environ["QUIET_START_HOUR_JST"] = str(start)
        os.environ["QUIET_END_HOUR_JST"] = str(end)
        self.el.TRAIL_ENABLED = True
        self.runner._refresh_trailing_status()
        self.assertFalse(self.el.TRAIL_ENABLED)

    def test_distance_multiplier_applied(self):
        os.environ["QUIET_START_HOUR_JST"] = "0"
        os.environ["QUIET_END_HOUR_JST"] = "0"
        self.position.update({
            "instrument": "EUR_USD",
            "long": {"units": "1", "averagePrice": "1.2000", "tradeIDs": ["t1"]},
            "pl": "0",
            "entry_time": "2024-01-01T00:00:00Z",
        })
        market = {"prices": [{"bids": [{"price": "1.2015"}], "asks": [{"price": "1.2015"}]}]}
        indicators = {"atr": [0.001]}
        self.el.TRAIL_ENABLED = True
        self.el.process_exit(indicators, market)
        calls = self.el.order_manager.calls
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], 10)

if __name__ == "__main__":
    unittest.main()

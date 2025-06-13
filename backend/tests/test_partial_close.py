import importlib
import os
import sys
import types
import unittest


class DummyResp:
    def __init__(self):
        self.ok = True
        self.status_code = 200
        self.text = ''
    def json(self):
        return {}
    def raise_for_status(self):
        pass

class TestPartialClose(unittest.TestCase):
    def setUp(self):
        self._added = []
        def add(name, mod):
            sys.modules[name] = mod
            self._added.append(name)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")
        self._old_pair = os.environ.get("DEFAULT_PAIR")
        os.environ["TRAIL_ENABLED"] = "true"
        os.environ["TRAIL_TRIGGER_PIPS"] = "10"
        os.environ["TRAIL_DISTANCE_PIPS"] = "6"
        os.environ["PARTIAL_CLOSE_PIPS"] = "10"
        os.environ["PARTIAL_CLOSE_RATIO"] = "0.5"
        os.environ["EARLY_EXIT_ENABLED"] = "false"
        os.environ["DEFAULT_PAIR"] = "EUR_USD"

        req = types.ModuleType("requests")
        req.post = req.put = req.get = lambda *a, **k: DummyResp()
        add("requests", req)
        add("pandas", types.ModuleType("pandas"))
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv)
        add("numpy", types.ModuleType("numpy"))

        log_stub = types.ModuleType("backend.logs.log_manager")
        log_stub.log_trade = lambda *a, **k: None
        log_stub.log_error = lambda *a, **k: None
        add("backend.logs.log_manager", log_stub)

        self.position = {}
        pm = types.ModuleType("backend.orders.position_manager")
        pm.get_position_details = lambda *a, **k: self.position
        add("backend.orders.position_manager", pm)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_exit_decision = lambda *a, **k: {"decision": "HOLD", "reason": ""}
        class _Resp:
            def __init__(self, d=None):
                self._d = d or {"decision": "HOLD"}
            def as_dict(self):
                return self._d
        oa.evaluate_exit = lambda *a, **k: _Resp()
        oa.EXIT_BIAS_FACTOR = 0.0
        add("backend.strategy.openai_analysis", oa)

        import backend.orders.order_manager as om
        importlib.reload(om)

        class DummyOM(om.OrderManager):
            def __init__(self):
                self.calls = []
            def place_trailing_stop(self, trade_id, instrument, distance_pips=None):
                self.calls.append(("trail", trade_id, instrument, distance_pips))
                return {}
            def close_partial(self, trade_id, units):
                self.calls.append(("partial", trade_id, units))
                return {}
            def exit_trade(self, *a, **k):
                pass
        self.DummyOM = DummyOM

        import backend.strategy.exit_logic as el
        importlib.reload(el)
        el.order_manager = DummyOM()
        self.el = el

    def tearDown(self):
        for name in self._added:
            sys.modules.pop(name, None)
        if self._old_pair is None:
            os.environ.pop("DEFAULT_PAIR", None)
        else:
            os.environ["DEFAULT_PAIR"] = self._old_pair

    def test_partial_close_and_trailing_stop(self):
        self.position.update({
            "instrument": "EUR_USD",
            "long": {"units": "2", "averagePrice": "1.2345", "tradeIDs": ["t1"]},
            "pl": "0",
            "entry_time": "2024-01-01T00:00:00Z"
        })
        market = {"prices": [{"bids": [{"price": "1.2365"}], "asks": [{"price": "1.2365"}]}]}
        self.el.process_exit({}, market)
        calls = self.el.order_manager.calls
        self.assertIn(("partial", "t1", 1), calls)
        self.assertIn(("trail", "t1", "EUR_USD", 6), calls)

if __name__ == "__main__":
    unittest.main()

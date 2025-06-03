import os
import sys
import types
import importlib
import unittest


class DummyResp:
    def __init__(self):
        self.ok = True
        self.status_code = 200
        self.text = ""

    def json(self):
        return {}

    def raise_for_status(self):
        pass


class TestTrailingStopAbsProfit(unittest.TestCase):
    def setUp(self):
        self._added = []

        def add(name, mod):
            sys.modules.pop(name, None)
            sys.modules[name] = mod
            self._added.append(name)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")
        os.environ["TRAIL_ENABLED"] = "true"
        os.environ["TRAIL_TRIGGER_PIPS"] = "22"
        os.environ["TRAIL_DISTANCE_PIPS"] = "6"
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

        self.position = {}
        pm = types.ModuleType("backend.orders.position_manager")
        pm.get_position_details = lambda *a, **k: self.position
        add("backend.orders.position_manager", pm)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_exit_decision = lambda *a, **k: {"decision": "HOLD", "reason": ""}
        oa.evaluate_exit = lambda ctx, bias_factor=1.0: types.SimpleNamespace(
            action="HOLD",
            confidence=0.0,
            reason="",
            as_dict=lambda: {"action": "HOLD", "confidence": 0.0, "reason": ""},
        )
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        import backend.orders.order_manager as om

        importlib.reload(om)

        class DummyOM(om.OrderManager):
            def __init__(self):
                self.calls = []

            def place_trailing_stop(self, trade_id, instrument, distance_pips=None):
                self.calls.append((trade_id, instrument, distance_pips))
                return {}

            def get_current_trailing_distance(self, trade_id, instrument):
                return None

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

    def test_long_position_triggers_on_positive_profit(self):
        self.position.update(
            {
                "instrument": "EUR_USD",
                "long": {"units": "1", "averagePrice": "1.2345", "tradeIDs": ["t1"]},
                "pl": "0",
                "entry_time": "2024-01-01T00:00:00Z",
            }
        )
        market = {
            "prices": [{"bids": [{"price": "1.2368"}], "asks": [{"price": "1.2368"}]}]
        }
        self.el.process_exit({}, market)
        calls = self.el.order_manager.calls
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "t1")
        self.assertEqual(calls[0][1], "EUR_USD")
        self.assertEqual(calls[0][2], 6)

    def test_trailing_stop_not_triggered_on_negative_profit(self):
        self.position.update(
            {
                "instrument": "EUR_USD",
                "long": {"units": "1", "averagePrice": "1.2345", "tradeIDs": ["t1"]},
                "pl": "0",
                "entry_time": "2024-01-01T00:00:00Z",
            }
        )
        market = {
            "prices": [{"bids": [{"price": "1.2330"}], "asks": [{"price": "1.2330"}]}]
        }
        self.el.process_exit({}, market)
        calls = self.el.order_manager.calls
        self.assertEqual(len(calls), 0)

    def test_no_trailing_below_threshold(self):
        self.position.update(
            {
                "instrument": "EUR_USD",
                "long": {"units": "1", "averagePrice": "1.2345", "tradeIDs": ["t1"]},
                "pl": "0",
                "entry_time": "2024-01-01T00:00:00Z",
            }
        )
        market = {
            "prices": [{"bids": [{"price": "1.2366"}], "asks": [{"price": "1.2366"}]}]
        }
        self.el.process_exit({}, market)
        self.assertEqual(len(self.el.order_manager.calls), 0)

    def test_no_trailing_when_distance_exceeds_profit(self):
        self.position.update(
            {
                "instrument": "EUR_USD",
                "long": {"units": "1", "averagePrice": "1.2345", "tradeIDs": ["t1"]},
                "pl": "0",
                "entry_time": "2024-01-01T00:00:00Z",
            }
        )
        # distance_pips は 15 とする
        self.el.TRAIL_DISTANCE_PIPS = 15.0
        market = {
            "prices": [{"bids": [{"price": "1.2357"}], "asks": [{"price": "1.2357"}]}]
        }
        self.el.process_exit({}, market)
        self.assertEqual(len(self.el.order_manager.calls), 0)

    def test_skip_when_distance_same(self):
        self.position.update(
            {
                "instrument": "EUR_USD",
                "long": {"units": "1", "averagePrice": "1.2345", "tradeIDs": ["t1"]},
                "pl": "0",
                "entry_time": "2024-01-01T00:00:00Z",
            }
        )
        market = {
            "prices": [{"bids": [{"price": "1.2368"}], "asks": [{"price": "1.2368"}]}]
        }
        class OM(self.DummyOM):
            def get_current_trailing_distance(self, trade_id, instrument):
                return 6

        self.el.order_manager = OM()
        self.el.process_exit({}, market)
        self.assertEqual(len(self.el.order_manager.calls), 0)


if __name__ == "__main__":
    unittest.main()

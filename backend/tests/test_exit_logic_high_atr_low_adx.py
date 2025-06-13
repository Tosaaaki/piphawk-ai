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

class TestHighAtrLowAdxExit(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
            sys.modules[name] = mod
            self._mods.append(name)

        os.environ.setdefault("OANDA_ACCOUNT_ID", "dummy")
        os.environ.setdefault("OANDA_API_KEY", "dummy")
        self._old_pair = os.environ.get("DEFAULT_PAIR")
        os.environ["EARLY_EXIT_ENABLED"] = "true"
        os.environ["HIGH_ATR_PIPS"] = "2"
        os.environ["LOW_ADX_THRESH"] = "20"
        os.environ["MIN_HOLD_SECONDS"] = "0"
        os.environ["DEFAULT_PAIR"] = "EUR_USD"

        add("requests", types.ModuleType("requests"))
        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)
        add("numpy", types.ModuleType("numpy"))

        log_stub = types.ModuleType("backend.logs.log_manager")
        log_stub.log_trade = lambda *a, **k: None
        log_stub.log_error = lambda *a, **k: None
        add("backend.logs.log_manager", log_stub)

        pm = types.ModuleType("backend.orders.position_manager")
        self.position = {}
        pm.get_position_details = lambda *a, **k: self.position
        add("backend.orders.position_manager", pm)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action="EXIT", reason="test", as_dict=lambda: {"action": "EXIT"})
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        import backend.orders.order_manager as om
        importlib.reload(om)
        class DummyOM(om.OrderManager):
            def __init__(self):
                self.calls = []
            def exit_trade(self, pos):
                self.calls.append(pos)
        self.DummyOM = DummyOM

        import backend.strategy.exit_logic as el
        importlib.reload(el)
        el.order_manager = DummyOM()
        self.el = el

    def tearDown(self):
        for n in self._mods:
            sys.modules.pop(n, None)
        sys.modules.pop("backend.strategy.exit_logic", None)
        os.environ.pop("HIGH_ATR_PIPS", None)
        os.environ.pop("LOW_ADX_THRESH", None)
        os.environ.pop("MIN_HOLD_SECONDS", None)
        if self._old_pair is None:
            os.environ.pop("DEFAULT_PAIR", None)
        else:
            os.environ["DEFAULT_PAIR"] = self._old_pair

    def test_exit_triggered_high_atr_low_adx(self):
        self.position.update({
            "instrument": "EUR_USD",
            "long": {"units": "1", "averagePrice": "1.0000", "tradeIDs": ["t1"]},
            "pl": "0",
            "entry_time": "2024-01-01T00:00:00Z"
        })
        indicators = {
            "ema_fast": FakeSeries([1.0000]),
            "atr": FakeSeries([0.02]),
            "bb_lower": FakeSeries([0.9900]),
            "bb_upper": FakeSeries([1.0100]),
            "adx": FakeSeries([10])
        }
        market = {"prices": [{"bids": [{"price": "1.0000"}], "asks": [{"price": "1.0001"}]}]}
        self.el.process_exit(indicators, market)
        self.assertEqual(len(self.el.order_manager.calls), 1)

if __name__ == "__main__":
    unittest.main()

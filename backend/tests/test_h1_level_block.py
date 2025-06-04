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


class TestH1LevelBlock(unittest.TestCase):
    def setUp(self):
        self._mods = []

        def add(name: str, mod: types.ModuleType):
            sys.modules[name] = mod
            self._mods.append(name)

        pandas_stub = types.ModuleType("pandas")
        pandas_stub.Series = FakeSeries
        add("pandas", pandas_stub)
        add("requests", types.ModuleType("requests"))
        dotenv_stub = types.ModuleType("dotenv")
        dotenv_stub.load_dotenv = lambda *a, **k: None
        add("dotenv", dotenv_stub)

        oa = types.ModuleType("backend.strategy.openai_analysis")
        oa.get_trade_plan = lambda *a, **k: {
            "entry": {"side": "short", "mode": "market"},
            "risk": {"tp_pips": 10, "sl_pips": 5},
        }
        oa.should_convert_limit_to_market = lambda ctx: True
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.calls = 0
            def enter_trade(self, *a, **k):
                self.calls += 1
                return {"order_id": "1"}
            def get_open_orders(self, instrument, side):
                return []
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)

        os.environ["PIP_SIZE"] = "0.01"
        os.environ["H1_BOUNCE_RANGE_PIPS"] = "3"

        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el

    def tearDown(self):
        for m in self._mods:
            sys.modules.pop(m, None)
        os.environ.pop("PIP_SIZE", None)
        os.environ.pop("H1_BOUNCE_RANGE_PIPS", None)

    def test_entry_blocked_near_h1_support(self):
        indicators = {"atr": FakeSeries([0.1])}
        candles = []
        market_data = {
            "prices": [{"instrument": "USD_JPY", "bids": [{"price": "1.005"}], "asks": [{"price": "1.015"}]}]
        }
        h1_ind = {"pivot": 1.02, "pivot_r1": 1.04}
        res = self.el.process_entry(
            indicators,
            candles,
            market_data,
            candles_dict={"M5": candles},
            tf_align=None,
            indicators_multi={"M5": indicators, "H1": h1_ind},
        )
        self.assertFalse(res)
        self.assertEqual(self.el.order_manager.calls, 0)


if __name__ == "__main__":
    unittest.main()

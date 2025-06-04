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


class TestPullbackBypass(unittest.TestCase):
    def setUp(self):
        self._mods = []
        def add(name, mod):
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
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "long", "mode": "market"}, "risk": {}}
        oa.should_convert_limit_to_market = lambda ctx: True
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.last_params = None
            def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False):
                self.last_params = strategy_params
                return {"order_id": "1"}
            def get_open_orders(self, instrument, side):
                return []
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)

        dp = types.ModuleType("backend.strategy.dynamic_pullback")
        dp.calculate_dynamic_pullback = lambda *a, **k: 5
        add("backend.strategy.dynamic_pullback", dp)

        os.environ["PIP_SIZE"] = "0.01"
        os.environ["PULLBACK_LIMIT_OFFSET_PIPS"] = "0"
        os.environ["PULLBACK_ATR_RATIO"] = "0"
        os.environ["BYPASS_PULLBACK_ADX_MIN"] = "55"

        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el
        self._mods.append("backend.strategy.entry_logic")

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        for name in [
            "pandas",
            "requests",
            "dotenv",
            "backend.strategy.openai_analysis",
            "backend.orders.order_manager",
            "backend.logs.log_manager",
            "backend.strategy.dynamic_pullback",
        ]:
            sys.modules.pop(name, None)
        os.environ.pop("PIP_SIZE", None)
        os.environ.pop("PULLBACK_LIMIT_OFFSET_PIPS", None)
        os.environ.pop("PULLBACK_ATR_RATIO", None)
        os.environ.pop("BYPASS_PULLBACK_ADX_MIN", None)

    def test_bypass_on_high_adx(self):
        indicators = {"atr": FakeSeries([0.1]), "adx": FakeSeries([60])}
        candles = []
        market_data = {"prices": [{"instrument": "USD_JPY", "bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}]}]}
        result = self.el.process_entry(
            indicators,
            candles,
            market_data,
            candles_dict={"M5": candles},
            tf_align=None,
        )
        self.assertTrue(result)
        self.assertEqual(self.el.order_manager.last_params["mode"], "market")
        self.assertIsNone(self.el.order_manager.last_params.get("limit_price"))


if __name__ == "__main__":
    unittest.main()

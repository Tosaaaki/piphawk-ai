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
    def __len__(self):
        return len(self._data)


class TestRegimeOverride(unittest.TestCase):
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
        oa.get_trade_plan = lambda *a, **k: {
            "regime": {"market_condition": "range"},
            "entry": {"side": "long", "mode": "market"},
            "risk": {"tp_pips": 10, "sl_pips": 5},
        }
        oa.should_convert_limit_to_market = lambda ctx: True
        oa.evaluate_exit = lambda *a, **k: types.SimpleNamespace(action="HOLD", confidence=0.0, reason="")
        oa.EXIT_BIAS_FACTOR = 1.0
        add("backend.strategy.openai_analysis", oa)

        om = types.ModuleType("backend.orders.order_manager")
        class DummyMgr:
            def __init__(self):
                self.last_params = None
            def enter_trade(self, side, lot_size, market_data, strategy_params, force_limit_only=False, with_oco=True):
                self.last_params = strategy_params
                return {"order_id": "1"}
            def get_open_orders(self, instrument, side):
                return []
        om.OrderManager = DummyMgr
        add("backend.orders.order_manager", om)

        log_mod = types.ModuleType("backend.logs.log_manager")
        log_mod.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_mod)

        comp = types.ModuleType("signals.composite_mode")
        comp.decide_trade_mode_detail = lambda *_a, **_k: ("trend_follow", 0.8, [])
        comp.decide_trade_mode = lambda *_a, **_k: "trend_follow"
        add("signals.composite_mode", comp)

        dp = types.ModuleType("backend.strategy.dynamic_pullback")
        dp.calculate_dynamic_pullback = lambda *a, **k: 0.0
        add("backend.strategy.dynamic_pullback", dp)

        os.environ["PIP_SIZE"] = "0.01"
        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        os.environ.pop("PIP_SIZE", None)

    def test_override_range_with_local_trend(self):
        indicators = {
            "atr": FakeSeries([0.1]),
            "momentum": {"score": 0.6},
        }
        candles = []
        market_data = {
            "prices": [{"instrument": "USD_JPY", "bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}]}]
        }
        market_cond = {"market_condition": "range"}
        res = self.el.process_entry(
            indicators,
            candles,
            market_data,
            market_cond=market_cond,
            candles_dict={"M5": candles},
            tf_align=None,
        )
        self.assertTrue(res)
        self.assertEqual(market_cond["market_condition"], "trend")
        self.assertIsNotNone(self.el.order_manager.last_params)


if __name__ == "__main__":
    unittest.main()

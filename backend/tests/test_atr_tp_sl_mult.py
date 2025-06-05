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

class TestAtrTpSlMult(unittest.TestCase):
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
        oa.get_trade_plan = lambda *a, **k: {"entry": {"side": "long", "mode": "market"}, "risk": {"tp_pips": None, "sl_pips": None}}
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

        # trend_pullback フィルターを常に True を返すスタブに置き換え
        tp_mod = types.ModuleType("backend.filters.trend_pullback")
        tp_mod.should_enter_long = lambda *a, **k: True
        add("backend.filters.trend_pullback", tp_mod)

        os.environ["PIP_SIZE"] = "0.01"
        os.environ["ATR_MULT_TP"] = "0.8"
        os.environ["ATR_MULT_SL"] = "1.1"
        os.environ["MIN_ATR_MULT"] = "1.1"

        # risk_manager.is_high_vol_session を常に False を返すように上書き
        import backend.risk_manager as rm
        self._risk_manager = rm
        self._orig_is_high_vol = rm.is_high_vol_session
        rm.is_high_vol_session = lambda: False

        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el
        self._mods.append("backend.strategy.entry_logic")

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        # risk_manager.is_high_vol_session を元に戻す
        if hasattr(self, "_risk_manager"):
            self._risk_manager.is_high_vol_session = self._orig_is_high_vol
        os.environ.pop("PIP_SIZE", None)
        os.environ.pop("ATR_MULT_TP", None)
        os.environ.pop("ATR_MULT_SL", None)
        os.environ.pop("MIN_ATR_MULT", None)
        sys.modules.pop("backend.strategy.entry_logic", None)

    def test_atr_based_tp_sl(self):
        indicators = {
            "atr": FakeSeries([0.05]),
        }
        candles = []
        market_data = {
            "prices": [{"instrument": "USD_JPY", "bids": [{"price": "1.0"}], "asks": [{"price": "1.01"}]}]
        }
        result = self.el.process_entry(
            indicators,
            candles,
            market_data,
            candles_dict={"M5": candles},
            tf_align=None,
        )
        self.assertTrue(result)
        self.assertAlmostEqual(self.el.order_manager.last_params["tp_pips"], 4.0)
        self.assertAlmostEqual(self.el.order_manager.last_params["sl_pips"], 5.5)

if __name__ == "__main__":
    unittest.main()

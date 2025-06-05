import os
import sys
import types
import importlib
import tempfile
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


class TestScalpMode(unittest.TestCase):
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

        log_stub = types.ModuleType("backend.logs.log_manager")
        log_stub.log_trade = lambda *a, **k: None
        add("backend.logs.log_manager", log_stub)

        os.environ["PIP_SIZE"] = "0.01"
        os.environ["SCALP_MODE"] = "true"
        os.environ["SCALP_ADX_MIN"] = "30"
        os.environ["SCALP_TP_PIPS"] = "2"
        os.environ["SCALP_SL_PIPS"] = "1"

        import backend.strategy.entry_logic as el
        importlib.reload(el)
        self.el = el
        self._mods.append("backend.strategy.entry_logic")

    def tearDown(self):
        for name in self._mods:
            sys.modules.pop(name, None)
        for key in [
            "PIP_SIZE",
            "SCALP_MODE",
            "SCALP_ADX_MIN",
            "SCALP_TP_PIPS",
            "SCALP_SL_PIPS",
        ]:
            os.environ.pop(key, None)

    def test_scalp_entry_uses_fixed_tp_sl(self):
        indicators = {"adx": FakeSeries([35])}
        candles = []
        market_data = {
            "prices": [{"instrument": "USD_JPY", "bids": [{"price": "1"}], "asks": [{"price": "1.01"}]}]
        }
        result = self.el.process_entry(
            indicators,
            candles,
            market_data,
            market_cond={"market_condition": "trend", "trend_direction": "long"},
        )
        self.assertTrue(result)
        self.assertEqual(self.el.order_manager.last_params["tp_pips"], 2.0)
        self.assertEqual(self.el.order_manager.last_params["sl_pips"], 1.0)
        self.assertEqual(self.el.order_manager.last_params["mode"], "market")


if __name__ == "__main__":
    unittest.main()

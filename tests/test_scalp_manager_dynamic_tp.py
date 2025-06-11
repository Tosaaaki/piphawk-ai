import importlib
import sys
import types
import os
os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")

import execution.scalp_manager as sm

class DummyOM:
    def __init__(self):
        self.params = None

    def place_market_with_tp_sl(self, instrument, units, side, tp_pips, sl_pips, comment_json=None):
        self.params = {
            "tp": tp_pips,
            "sl": sl_pips,
        }
        return {
            "lastTransactionID": "t1",
            "orderFillTransaction": {
                "price": "1",
                "tradeOpened": {"tradeID": "t1"},
            },
        }

    def close_position(self, *a, **k):
        return None

class FakeSeries:
    def __init__(self, val):
        class _IL:
            def __getitem__(self, idx):
                return val
        self.iloc = _IL()
        self._val = val

    def __getitem__(self, idx):
        return self._val


def test_dynamic_tp_sl(monkeypatch):
    dummy_mod = types.SimpleNamespace(
        OrderManager=DummyOM,
        get_pip_size=lambda i: 0.01 if i.endswith("_JPY") else 0.0001,
    )
    monkeypatch.setitem(sys.modules, "backend.orders.order_manager", dummy_mod)
    importlib.reload(sm)
    sm.order_mgr = sm.OrderManager()

    fetch_mod = types.SimpleNamespace(fetch_candles=lambda *a, **k: [{}] * 30)
    ind_mod = types.SimpleNamespace(calculate_indicators=lambda *a, **k: {"atr": FakeSeries(0.04)})
    scalp_mod = types.SimpleNamespace(get_scalp_plan=lambda *a, **k: {"tp_pips": 2.0, "sl_pips": 1.0})

    sys.modules["backend.market_data.candle_fetcher"] = fetch_mod
    sys.modules["backend.indicators.calculate_indicators"] = ind_mod
    sys.modules["backend.strategy.openai_scalp_analysis"] = scalp_mod

    monkeypatch.setenv("MIN_SL_PIPS", "5")
    monkeypatch.setenv("ATR_SL_MULTIPLIER", "0")

    sm.enter_scalp_trade("USD_JPY", "long")
    assert sm.order_mgr.params["tp"] == 2.0
    assert sm.order_mgr.params["sl"] == 5.0

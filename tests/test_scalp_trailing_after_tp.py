import importlib
import os
import sys
import types

os.environ.setdefault("OANDA_API_KEY", "x")
os.environ.setdefault("OANDA_ACCOUNT_ID", "x")

import execution.scalp_manager as sm


class DummyOM:
    def __init__(self):
        self.called = None
    def place_market_with_tp_sl(self, instrument, units, side, tp_pips, sl_pips, comment_json=None, price_bound=None):
        return {
            "lastTransactionID": "t1",
            "orderFillTransaction": {"price": "1.0", "tradeOpened": {"tradeID": "t1"}},
        }
    def attach_trailing_after_tp(self, trade_id, instrument, entry_price, atr_pips):
        self.called = (trade_id, instrument, entry_price, atr_pips)
    def close_position(self, *a, **k):
        return None

class FakeSeries:
    def __init__(self, val):
        self._val = val
        class _IL:
            def __getitem__(self, idx):
                return val
        self.iloc = _IL()
    def __getitem__(self, idx):
        return self._val

def test_trailing_attached_on_tp(monkeypatch):
    dummy_mod = types.SimpleNamespace(
        OrderManager=DummyOM,
        get_pip_size=lambda i: 0.01 if i.endswith("_JPY") else 0.0001,
    )
    monkeypatch.setitem(sys.modules, "backend.orders.order_manager", dummy_mod)
    importlib.reload(sm)
    sm.order_mgr = sm.OrderManager()

    fetch_mod = types.SimpleNamespace(fetch_candles=lambda *a, **k: [{}] * 30)
    ind_mod = types.SimpleNamespace(calculate_indicators=lambda *a, **k: {"atr": FakeSeries(0.04)})
    scalp_mod = types.SimpleNamespace(get_scalp_plan=lambda *a, **k: {"tp_pips": 1.0, "sl_pips": 1.0})
    tick_mod = types.SimpleNamespace(fetch_tick_data=lambda *a, **k: {"prices": [{"bids": [{"price": "1.011"}], "asks": [{"price": "1.011"}]}]})

    sys.modules["backend.market_data.candle_fetcher"] = fetch_mod
    sys.modules["backend.indicators.calculate_indicators"] = ind_mod
    sys.modules["backend.strategy.openai_scalp_analysis"] = scalp_mod
    sys.modules["backend.market_data.tick_fetcher"] = tick_mod

    monkeypatch.setenv("TRAIL_AFTER_TP", "true")
    sm.enter_scalp_trade("USD_JPY", "long")
    assert sm.order_mgr.called == ("t1", "USD_JPY", 1.0, 4.0)

